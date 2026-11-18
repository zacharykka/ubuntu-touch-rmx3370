/* bitra camera-preview fix.
 *
 * Problem: on this Halium 11 GSI, libhybris' DecodingService never calls its
 * own createBufferQueue(), so DecodingService::getIGraphicBufferConsumer()
 * returns SUCCESS while writing a NULL IGraphicBufferConsumer. HybrisVideoSink
 * passes that NULL into GLConsumer, and android::ConsumerBase's constructor in
 * libgui.so dereferences it (instruction at libgui+0x885b4, ldr x8,[x0] with
 * x0 = 0). Every QML VideoOutput bound to a Camera segfaulted about two seconds
 * after start.
 *
 * Fix: intercept gl_consumer_create_by_id_with_igbc. When the incoming wrapper
 * holds a NULL consumer, build a real BufferQueue via libgui's exported
 * android::BufferQueue::createBufferQueue() and store the consumer in the
 * wrapper before forwarding. sp<T> is a single pointer, so one 8-byte slot
 * stands in for each sp<>.
 *
 * Resolving the function: libhybris loads libgui.so in its own linker
 * namespace, so glibc's dlopen("libgui.so") returns NULL and the symbol is
 * invisible to dlsym(RTLD_DEFAULT). libhybris does export android_dlopen() and
 * android_dlsym() (the latter named "android_dlsym" after stripping), reachable
 * through a handle on libhybris-common.so.1 -- but only once the media path has
 * started, so resolution has to happen at first use rather than at load time.
 * A static offset from the load base is kept as a fallback and as a cross-check;
 * on the GSI this was developed against both routes agree exactly
 * (android_dlsym == load base + 0x68cd0).
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

#define SYM_CREATE_BQ \
    "_ZN7android11BufferQueue17createBufferQueueEPNS_2spINS_22IGraphicBufferProducerEEEPNS1_INS_22IGraphicBufferConsumerEEEb"
#define LIBGUI_SONAME  "libgui.so"
#define LIBGUI_ABS     "/android/system/lib64/libgui.so"
#define OFF_CREATE_BQ  0x68cd0UL

typedef void *(*android_dlopen_fn)(const char *name, int flag);
typedef void *(*android_dlsym_fn)(void *handle, const char *symbol);
typedef void (*create_bq_fn)(void **outProducer, void **outConsumer, int isSurfaceFlinger);
typedef void *(*real_glc_fn)(unsigned int texture_id, void *wrapper);

/* Load base of a shared object, from the mapping whose file offset is 0. */
static unsigned long lib_base(const char *soname)
{
    FILE *fp = fopen("/proc/self/maps", "r");
    if (!fp) return 0;

    char line[512];
    unsigned long at_zero = 0, lowest = 0;

    while (fgets(line, sizeof line, fp)) {
        if (!strstr(line, soname)) continue;
        unsigned long lo, off;
        if (sscanf(line, "%lx-%*lx %*s %lx", &lo, &off) != 2) continue;
        /* Prefer the mapping at file offset 0; a segment mapped at a non-zero
         * offset can sit below it in some layouts. */
        if (off == 0 && (!at_zero || lo < at_zero)) at_zero = lo;
        if (!lowest || lo < lowest) lowest = lo;
    }
    fclose(fp);
    return at_zero ? at_zero : lowest;
}

static create_bq_fn create_bq_by_name(void)
{
    void *h = dlopen("libhybris-common.so.1", RTLD_LAZY);
    if (!h) return NULL;

    android_dlopen_fn ado = (android_dlopen_fn)dlsym(h, "android_dlopen");
    android_dlsym_fn  ads = (android_dlsym_fn)dlsym(h, "android_dlsym");
    if (!ado || !ads) return NULL;

    void *drv = ado(LIBGUI_ABS, 1);
    if (!drv) drv = ado(LIBGUI_SONAME, 1);
    if (!drv) return NULL;

    return (create_bq_fn)ads(drv, SYM_CREATE_BQ);
}

static create_bq_fn resolve_create_bq(void)
{
    static create_bq_fn fn;
    static int tried;

    if (fn) return fn;
    if (tried) return NULL;
    tried = 1;

    fn = create_bq_by_name();

    unsigned long base = lib_base(LIBGUI_SONAME);
    create_bq_fn by_offset = base ? (create_bq_fn)(base + OFF_CREATE_BQ) : NULL;

    if (fn && by_offset && fn != by_offset) {
        /* Both routes work but disagree: trust the symbol table, not the
         * offset, which is tied to one libgui build. */
        fprintf(stderr, "[camfix] name/offset disagreement, using name\n");
    } else if (fn) {
        fprintf(stderr, "[camfix] createBufferQueue resolved by name\n");
    } else if (by_offset) {
        fprintf(stderr, "[camfix] createBufferQueue from offset (base=%#lx)\n", base);
        fn = by_offset;
    } else {
        fprintf(stderr, "[camfix] libgui not mapped; cannot fix\n");
    }
    return fn;
}

static real_glc_fn resolve_real_glc(void)
{
    static real_glc_fn fn;
    static int tried;
    if (tried) return fn;
    tried = 1;

    const char *libs[] = { "libMediaHub.so.5", "libmedia.so.1", NULL };
    for (int i = 0; libs[i] && !fn; i++) {
        void *h = dlopen(libs[i], RTLD_LAZY | RTLD_NOLOAD);
        if (!h) h = dlopen(libs[i], RTLD_LAZY);
        if (h)
            fn = (real_glc_fn)dlsym(h, "gl_consumer_create_by_id_with_igbc");
    }
    return fn;
}

void *gl_consumer_create_by_id_with_igbc(unsigned int texture_id, void *wrapper)
{
    if (wrapper && !*(void **)wrapper) {
        create_bq_fn create_bq = resolve_create_bq();
        if (create_bq) {
            void *producer_sp[1] = { 0 };
            void *consumer_sp[1] = { 0 };
            create_bq(producer_sp, consumer_sp, 0);
            if (consumer_sp[0]) {
                *(void **)wrapper = consumer_sp[0];
            } else {
                fprintf(stderr, "[camfix] createBufferQueue produced no consumer\n");
            }
        }
    }

    real_glc_fn real = resolve_real_glc();
    if (!real) return NULL;
    return real(texture_id, wrapper);
}
