#!/usr/bin/env python3
"""f_mtp: only one MTP device can exist; fail cleanly instead of crashing."""
import sys

p = sys.argv[1]
s = open(p).read()


def sub(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f'anchor matched {n} times: {old[:60]!r}')
    s = s.replace(old, new)


# 1. A second MTP instance must not re-run __mtp_setup(): misc_register() of
#    the single /dev/mtp_usb fails with -EBUSY and the error path then cleared
#    _mtp_dev under the first, still-live instance.
sub('''static int __mtp_setup(struct mtp_instance *fi_mtp)
{
	struct mtp_dev *dev;
	int ret;

	dev = kzalloc(sizeof(*dev), GFP_KERNEL);
''', '''static int __mtp_setup(struct mtp_instance *fi_mtp)
{
	struct mtp_dev *dev;
	int ret;

	if (_mtp_dev) {
		pr_err("%s: an MTP function instance already exists\\n", __func__);
		return -EBUSY;
	}

	dev = kzalloc(sizeof(*dev), GFP_KERNEL);
''')

# 2. PTP shares the MTP device; without one, fail instead of dereferencing NULL.
sub('''	} else
		fi_mtp->dev = _mtp_dev;

	config_group_init_type_name(&fi_mtp->func_inst.group,''', '''	} else {
		if (!_mtp_dev) {
			kfree(fi_mtp);
			pr_err("Error: create the MTP function before PTP\\n");
			return ERR_PTR(-EINVAL);
		}
		fi_mtp->dev = _mtp_dev;
	}

	config_group_init_type_name(&fi_mtp->func_inst.group,''')

# 3. Only the instance that created the device initialises its mutex and tears
#    it down; a PTP instance freeing itself must not destroy the shared device.
sub('''	mutex_init(&fi_mtp->dev->read_mutex);

	return  &fi_mtp->func_inst;''', '''	if (mtp_config)
		mutex_init(&fi_mtp->dev->read_mutex);
	fi_mtp->owns_dev = mtp_config;

	return  &fi_mtp->func_inst;''')

sub('''	fi_mtp = to_fi_mtp(fi);
	kfree(fi_mtp->name);
	mtp_cleanup();
	kfree(fi_mtp);''', '''	fi_mtp = to_fi_mtp(fi);
	kfree(fi_mtp->name);
	if (fi_mtp->owns_dev)
		mtp_cleanup();
	kfree(fi_mtp);''')

sub('''struct mtp_instance {
	struct usb_function_instance func_inst;
	const char *name;
	struct mtp_dev *dev;''', '''struct mtp_instance {
	struct usb_function_instance func_inst;
	const char *name;
	struct mtp_dev *dev;
	bool owns_dev;	/* created _mtp_dev (MTP); PTP instances only borrow it */''')

open(p, 'w').write(s)
print('patched')
