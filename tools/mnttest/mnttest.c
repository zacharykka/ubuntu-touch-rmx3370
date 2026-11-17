/* Minimal mount(2) probe: report stat/open/mount results with raw errno. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	if (argc < 4) {
		fprintf(stderr, "usage: %s SRC DST FSTYPE [FLAGS]\n", argv[0]);
		return 2;
	}
	const char *src = argv[1], *dst = argv[2], *type = argv[3];
	unsigned long flags = argc > 4 ? strtoul(argv[4], NULL, 0) : MS_RDONLY;
	struct stat st;

	if (stat(src, &st))
		printf("stat(%s): errno=%d %s\n", src, errno, strerror(errno));
	else
		printf("stat(%s): mode=%o rdev=%u:%u\n", src, st.st_mode,
		       major(st.st_rdev), minor(st.st_rdev));

	int fd = open(src, O_RDONLY);
	printf("open(%s): %s\n", src, fd < 0 ? strerror(errno) : "ok");
	if (fd >= 0)
		close(fd);

	if (stat(dst, &st))
		printf("stat(%s): errno=%d %s\n", dst, errno, strerror(errno));

	errno = 0;
	int r = mount(src, dst, type, flags, NULL);
	printf("mount(%s, %s, %s, 0x%lx) = %d errno=%d (%s)\n", src, dst, type,
	       flags, r, r ? errno : 0, r ? strerror(errno) : "ok");
	return r ? 1 : 0;
}
