#ifndef SZERO_NATIVE_LAN_IDENTITY_H
#define SZERO_NATIVE_LAN_IDENTITY_H
#include "native_session_codec.h"
/* LAN principals are not Steam identities. Projection affects only a decoder's
 * exclusively-owned temporary DTO, never platform/account/native user state. */
int szero_lan_identity_valid(const unsigned char *value,size_t size);
/* Returns 1 on success, 0 on refusal; failure leaves the entire codec unchanged.
 * Search requires zero local members, membership requires exactly one. Raw
 * server members must all carry canonical LAN primaries, so projected input
 * cannot accidentally be projected a second time. */
int szero_lan_identity_project(SzeroSessionCodec *codec,
    const unsigned char *self_lan,size_t self_lan_size,
    const SzeroIdentityWire *native_self,int require_local);
#endif
