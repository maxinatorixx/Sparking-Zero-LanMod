"""Build all Win64 helpers using the existing MinGW compiler, without installing them."""
import argparse
from pathlib import Path
import subprocess

NATIVE = Path(__file__).resolve().parent / "native"
MINHOOK = ["vendor/minhook/src/" + name for name in
           ("buffer.c", "hook.c", "trampoline.c", "hde/hde64.c")]
SESSION = ["native_session_host.c", "native_session_adapter.c", "native_session_codec.c",
           "native_session_search.c", "native_session_inspect.c", "native_lan_identity.c",
           "native_lan_userinfo.c", "session_materializer.c", "native_session_wire.c",
           "native_lan_transport.c"]
# MinGW otherwise hashes the output path into its preferred image base, making
# byte identity depend on the staging directory. ASLR/relocations remain enabled.
IMAGE_BASES = {"backend_adapter": 0x301ac0000, "console_probe": 0x20b700000,
               "menu_bridge": 0x3b9e00000, "native_search": 0x3b91d0000,
               "service_trace": 0x2a8bf0000, "session_probe": 0x3766a0000}


def build(output, compiler="x86_64-w64-mingw32-gcc"):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    common = [compiler, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
              "-shared", "-static-libgcc", "-Wl,--no-insert-timestamp"]
    for name in ("backend_adapter", "service_trace", "native_search", "console_probe",
                 "menu_bridge", "session_probe"):
        sources = [name + ".c", "native_bindings.c"]
        flags = []
        libraries = ["-lbcrypt"]
        if name in ("backend_adapter", "service_trace"):
            sources += MINHOOK
        if name == "backend_adapter":
            sources += ["backend_response.c"]
        if name == "native_search":
            flags += ["-DSZERO_SESSION_V3"]
            sources += SESSION
        if name in ("backend_adapter", "native_search"):
            libraries += ["-lws2_32"]
        subprocess.run([*common, "-Wl,--image-base=" + hex(IMAGE_BASES[name]), *flags,
                        *(str(NATIVE / source) for source in sources),
                        "-o", str(output / (name + ".dll")), *libraries], check=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(NATIVE.parent.parent / ".build/native"))
    parser.add_argument("--compiler", default="x86_64-w64-mingw32-gcc")
    arguments = parser.parse_args()
    print(build(arguments.output, arguments.compiler))
