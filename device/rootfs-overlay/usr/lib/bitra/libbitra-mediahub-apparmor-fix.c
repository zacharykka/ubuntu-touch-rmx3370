/* bitra media-hub fix for kernels where SELinux is the major LSM.
 *
 * media-hub resolves a client's AppArmor context from dbus-daemon:
 * GetConnectionCredentials -> "LinuxSecurityLabel". dbus-daemon fills that from
 * SO_PEERSEC without checking which LSM is active, so on this kernel
 * (/sys/kernel/security/lsm = "capability,selinux") every client is reported as
 * the SELinux label "u:r:kernel:s0".
 *
 * media-hub (src/service/apparmor/lomiri.cpp) then does:
 *
 *     aa_splitcon(context.data(), NULL);      // return value discarded; it only
 *     appId = QString::fromUtf8(context);     // trims " (mode)" in place
 *
 * aa_splitcon() returns NULL for an SELinux label and leaves the buffer alone,
 * so appId = "u:r:kernel:s0". Its split('_') yields one part, and
 * Context::profile_name() reads app_id_parts[1] without a bounds check -- an
 * out-of-bounds QList read that hands stale bytes to QString::append, which
 * segfaults. Every player session (audio included) takes this path.
 *
 * Fix: interpose aa_splitcon. When the real function cannot parse the label
 * AND AppArmor is not enabled on this kernel, rewrite the buffer in place to
 * "unconfined" -- the truthful answer when no AppArmor policy is loaded. media-
 * hub then takes its documented unconfined path ("Client allowed access since
 * it's unconfined") and never reaches profile_name().
 *
 * On a system where AppArmor is the major LSM, aa_splitcon parses every label
 * and aa_is_enabled() is true, so this shim never changes anything.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef char *(*aa_splitcon_fn)(char *con, char **mode);
typedef int (*aa_is_enabled_fn)(void);

static const char UNCONFINED[] = "unconfined";

static int apparmor_enabled(void)
{
    static int cached = -1;
    if (cached < 0) {
        aa_is_enabled_fn f = (aa_is_enabled_fn)dlsym(RTLD_DEFAULT, "aa_is_enabled");
        /* If we cannot ask, assume AppArmor is on and stay out of the way. */
        cached = f ? (f() == 1) : 1;
    }
    return cached;
}

char *aa_splitcon(char *con, char **mode)
{
    static aa_splitcon_fn real;
    if (!real)
        real = (aa_splitcon_fn)dlsym(RTLD_NEXT, "aa_splitcon");

    char *out = real ? real(con, mode) : NULL;
    if (out || !con || apparmor_enabled())
        return out;

    /* The label did not parse and AppArmor is not running. The buffer is the
     * caller's QByteArray holding the dbus label; "unconfined" is shorter than
     * any label that can reach here unparsed, so it fits. */
    size_t len = strlen(con);
    if (len < sizeof(UNCONFINED) - 1)
        return out;

    static int logged;
    if (!logged) {
        logged = 1;
        fprintf(stderr, "[bitra-aafix] AppArmor is not enabled; treating "
                        "non-AppArmor label '%s' as unconfined\n", con);
    }
    memcpy(con, UNCONFINED, sizeof(UNCONFINED));
    if (mode) *mode = NULL;
    return con;
}
