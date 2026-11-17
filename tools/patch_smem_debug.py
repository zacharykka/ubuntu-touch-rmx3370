#!/usr/bin/env python3
"""Temporary diagnostics for drivers/soc/qcom/smem.c (read-only dumps, no behaviour change)."""
import sys

path = sys.argv[1]
src = open(path).read()


def sub(old, new):
    global src
    n = src.count(old)
    if n != 1:
        sys.exit(f'anchor matched {n} times: {old[:60]!r}')
    src = src.replace(old, new)


HELPER = r'''
/* DEBUG(ut-bitra): read-only dump of a private SMEM partition. Temporary. */
static void smem_dbg_dump(struct smem_partition_desc *p_desc, const char *tag)
{
	struct smem_partition_header *phdr = p_desc->virt_base;
	void *p = phdr;
	void *p_end = p + p_desc->size;
	u32 free_unc = le32_to_cpu(phdr->offset_free_uncached);
	u32 free_cac = le32_to_cpu(phdr->offset_free_cached);
	struct smem_private_entry *e;
	int n;

	pr_info("smem-dbg[%s]: hosts %u:%u hdr.size=%u desc.size=%u free_unc=0x%x free_cac=0x%x cacheline=%u\n",
		tag, le16_to_cpu(phdr->host0), le16_to_cpu(phdr->host1),
		le32_to_cpu(phdr->size), p_desc->size, free_unc, free_cac,
		p_desc->cacheline);

	e = phdr_to_first_uncached_entry(phdr);
	for (n = 0; n < 512 && (void *)(e + 1) <= p + free_unc &&
		    (void *)(e + 1) <= p_end; n++) {
		pr_info("smem-dbg[%s]: U%03d off=0x%05lx canary=%04x item=%u size=%u pd=%u ph=%u\n",
			tag, n, (unsigned long)((void *)e - p), e->canary,
			le16_to_cpu(e->item), le32_to_cpu(e->size),
			le16_to_cpu(e->padding_data), le16_to_cpu(e->padding_hdr));
		if (e->canary != SMEM_PRIVATE_CANARY)
			break;
		e = (void *)e + sizeof(*e) + le16_to_cpu(e->padding_hdr) +
		    le32_to_cpu(e->size);
	}
	pr_info("smem-dbg[%s]: uncached walk ended at off=0x%05lx after %d entries\n",
		tag, (unsigned long)((void *)e - p), n);

	if (!p_desc->cacheline || free_cac > p_desc->size)
		return;
	e = phdr_to_first_cached_entry(phdr, p_desc->cacheline);
	for (n = 0; n < 512 && (void *)e > p + free_cac && (void *)e >= p &&
		    (void *)(e + 1) <= p_end; n++) {
		pr_info("smem-dbg[%s]: C%03d off=0x%05lx canary=%04x item=%u size=%u pd=%u ph=%u\n",
			tag, n, (unsigned long)((void *)e - p), e->canary,
			le16_to_cpu(e->item), le32_to_cpu(e->size),
			le16_to_cpu(e->padding_data), le16_to_cpu(e->padding_hdr));
		if (e->canary != SMEM_PRIVATE_CANARY)
			break;
		e = cached_entry_next(e, p_desc->cacheline);
	}
	pr_info("smem-dbg[%s]: cached walk ended at off=0x%05lx after %d entries\n",
		tag, (unsigned long)((void *)e - p), n);
}

static int qcom_smem_alloc_private('''

sub('\nstatic int qcom_smem_alloc_private(', HELPER)

sub('''	hdr->canary = SMEM_PRIVATE_CANARY;
''', '''	pr_info("smem-dbg: alloc item=%u size=%zu at off=0x%lx free_unc=0x%x hdr_at_end=%d\\n",
		item, size, (unsigned long)((void *)hdr - (void *)phdr),
		le32_to_cpu(phdr->offset_free_uncached), hdr == end);
	hdr->canary = SMEM_PRIVATE_CANARY;
''')

sub('''invalid_canary:
	dev_err(smem->dev, "Found invalid canary in hosts %hu:%hu partition\\n",
			le16_to_cpu(phdr->host0), le16_to_cpu(phdr->host1));

	return ERR_PTR(-EINVAL);''', '''invalid_canary:
	{
		static bool smem_dbg_dumped;

		pr_info("smem-dbg: lookup item=%u hit bad canary at off=0x%lx (canary=%04x item=%u size=%u)\\n",
			item, (unsigned long)((void *)e - (void *)phdr), e->canary,
			le16_to_cpu(e->item), le32_to_cpu(e->size));
		if (!smem_dbg_dumped) {
			smem_dbg_dumped = true;
			smem_dbg_dump(p_desc, "first-failure");
		}
	}
	dev_err(smem->dev, "Found invalid canary in hosts %hu:%hu partition\\n",
			le16_to_cpu(phdr->host0), le16_to_cpu(phdr->host1));

	return ERR_PTR(-EINVAL);''')

sub('''	ret = qcom_smem_enumerate_partitions(smem, SMEM_HOST_APPS);
	if (ret < 0 && ret != -ENOENT)
		return ret;

	__smem = smem;
''', '''	ret = qcom_smem_enumerate_partitions(smem, SMEM_HOST_APPS);
	if (ret < 0 && ret != -ENOENT)
		return ret;

	if (smem->global_partition_desc.virt_base)
		smem_dbg_dump(&smem->global_partition_desc, "probe");

	__smem = smem;
''')

open(path, 'w').write(src)
print('patched')
