#!/usr/bin/env python3
"""Fix the SMEM_SENSOR layout for bitra and stop the sensor drivers from overrunning SMEM items."""
import sys

root = sys.argv[1]


def edit(rel, old, new):
    p = f'{root}/{rel}'
    s = open(p).read()
    n = s.count(old)
    if n != 1:
        sys.exit(f'{rel}: anchor matched {n} times: {old[:70]!r}')
    open(p, 'w').write(s.replace(old, new))


H = 'drivers/soc/oplus/sensor/oplus_sensor_devinfo.h'
edit(H, '#define SOURCE_NUM 3\n',
     '/*\n * Number of alternative parts per sensor slot. This sizes struct sensor_info,\n'
     ' * which is a layout contract with the SLPI sensor firmware through SMEM_SENSOR.\n'
     ' * bitra (21619) firmware allocates that item for SOURCE_NUM 2 (4768 bytes).\n */\n'
     '#define SOURCE_NUM 2\n')

C = 'drivers/soc/oplus/sensor/oplus_sensor_devinfo.c'
edit(C, '''	chip = (struct sensor_info *)(smem_addr);

	memset(chip, 0, sizeof(struct sensor_info));
''', '''	if (smem_size < sizeof(struct sensor_info)) {
		pr_err("%s: SMEM_SENSOR is %zu bytes but struct sensor_info needs %zu, not touching it\\n",
		       __func__, smem_size, sizeof(struct sensor_info));
		return -EINVAL;
	}

	chip = (struct sensor_info *)(smem_addr);

	memset(chip, 0, sizeof(struct sensor_info));
''')

F = 'drivers/soc/oplus/sensor/oplus_sensor_feedback/sensor_feedback.c'
edit(F, '''	memcpy((void *)&sensor_fb_cxt->fb_smem, (void *)fb_event, smem_size);''',
     '''	memcpy((void *)&sensor_fb_cxt->fb_smem, (void *)fb_event,
	       min(smem_size, sizeof(sensor_fb_cxt->fb_smem)));''')
print('patched')
