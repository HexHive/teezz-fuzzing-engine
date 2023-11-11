import sys
import os
import glob
import logging
import shutil

from typing import List

################################################################################
# LOGGING
################################################################################

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

################################################################################
# CODE
################################################################################


def listdir_abs(dir_: str) -> List[str]:
    return sorted([os.path.join(dir_, d) for d in os.listdir(dir_)])


def has_callbacks(dir: str):
    # if we see the substring "_cb_" in the recordings, the high-level
    # recordings are split in separate directories
    return len([d for d in glob.glob(f"{dir}/*/*/*") if "_cb_" in d]) > 0


def merge_callbacks(dir: str):
    # obtain dirs and sort numerically by sequence number
    interaction_dirs = sorted(
        [d for d in glob.glob(f"{dir}/*/*")], key=lambda d: int(os.path.basename(d))
    )

    if len(interaction_dirs) < 2:
        # nothing to merge
        return

    cb_interact_dir = interaction_dirs.pop(0)
    hal_interact_dir = interaction_dirs.pop(0)

    while True:
        tmp_dirs = glob.glob(f"{cb_interact_dir}/*_cb_*")

        if len(tmp_dirs) == 0:
            # not a callback, advance
            cb_interact_dir = hal_interact_dir
            if not interaction_dirs:
                break
            hal_interact_dir = interaction_dirs.pop(0)
            continue
        elif len(tmp_dirs) > 1:
            log.error("multiple *_cb_* dirs. error in recording?")
            import ipdb

            ipdb.set_trace()

        hal_name = os.path.basename(tmp_dirs[0]).split("_")[0]

        tmp_dirs = glob.glob(f"{hal_interact_dir}/*")
        if len(tmp_dirs) != 1:
            log.error("multiple hal dirs. error in recording?")
            import ipdb

            ipdb.set_trace()
        assert len(tmp_dirs) == 1, f"more than 1 hal dir: {len(tmp_dirs)}"
        hal_dir = tmp_dirs[0]

        if hal_name in hal_dir:
            shutil.move(hal_dir, cb_interact_dir)
            shutil.rmtree(os.path.dirname(hal_dir))

            if not interaction_dirs:
                break
            cb_interact_dir = interaction_dirs.pop(0)
        else:
            cb_interact_dir = hal_interact_dir

        if not interaction_dirs:
            break
        hal_interact_dir = interaction_dirs.pop(0)


def rearrange(idir: str):
    hal_ioctl_dirs: List[str] = listdir_abs(idir)
    hal_dirs = [
        dir_ for dir_ in hal_ioctl_dirs if "ioctl" not in os.path.basename(dir_)
    ]

    if len(hal_dirs) > 2:
        # we expect two hal dirs max

        # there is a bug in the hal recorder that causes dumping of the same
        # cb multiple times. we work around this by keeping the first hal
        # recording dir and deleting all others

        # TODO: does this still happen?
        import ipdb

        ipdb.set_trace()
        cb_hal_dirs = [cb for cb in hal_dirs if "__hidl_cb" in cb]
        if len(cb_hal_dirs) <= 1:
            # apparently we do not have multiple hal cb dirs
            # investigate this situation if it ever happens
            import ipdb

            ipdb.set_trace()

        for cb in cb_hal_dirs[1:]:
            shutil.rmtree(cb)

    # look for "*ioctl*" dir and take the first one
    ioctl_dir_l = [dir_ for dir_ in hal_ioctl_dirs if "ioctl" in os.path.basename(dir_)]
    if not ioctl_dir_l:
        # we do not have an ioctl dir for this interaction, delete it
        shutil.rmtree(idir)
        return

    if len(ioctl_dir_l) != 1:
        import ipdb

        ipdb.set_trace()

    ioctl_dir = ioctl_dir_l[0]
    ioctl_onenter = os.path.join(ioctl_dir, "onenter")
    ioctl_onleave = os.path.join(ioctl_dir, "onleave")

    hal_noncb_dir = None
    hal_cb_dir = None
    for hal_dir in hal_dirs:
        if "_cb_" in os.path.basename(hal_dir):
            hal_cb_dir = hal_dir
        else:
            hal_noncb_dir = hal_dir

    if (
        hal_noncb_dir
        and os.path.isdir(hal_noncb_dir)
        and hal_cb_dir
        and os.path.isdir(hal_cb_dir)
    ):
        hal_noncb_onenter = os.path.join(hal_noncb_dir, "onenter")
        hal_noncb_onleave = os.path.join(hal_noncb_dir, "onleave")
        hal_cb_onenter = os.path.join(hal_cb_dir, "onenter")

        # move onenter from hal_cb into hal_noncb if it exists
        # delete onleave from noncb
        shutil.rmtree(hal_noncb_onleave)
        # move onenter of cb to onleave of noncb
        shutil.move(hal_cb_onenter, hal_noncb_onleave)
        # remove cb dir
        shutil.rmtree(hal_cb_dir)

        hal_name = os.path.basename(hal_noncb_dir)
        dst = os.path.join(ioctl_onenter, f"hal_{hal_name}")
        shutil.move(hal_noncb_onenter, dst)
        dst = os.path.join(ioctl_onleave, f"hal_{hal_name}")
        shutil.move(hal_noncb_onleave, dst)
        shutil.rmtree(hal_noncb_dir)
    elif hal_noncb_dir and os.path.isdir(hal_noncb_dir):
        hal_name = os.path.basename(hal_noncb_dir)
        hal_noncb_onenter = os.path.join(hal_noncb_dir, "onenter")
        hal_noncb_onleave = os.path.join(hal_noncb_dir, "onleave")
        dst = os.path.join(ioctl_onenter, f"hal_{hal_name}")
        shutil.move(hal_noncb_onenter, dst)
        dst = os.path.join(ioctl_onleave, f"hal_{hal_name}")
        shutil.move(hal_noncb_onleave, dst)
        shutil.rmtree(hal_noncb_dir)

    shutil.move(ioctl_onenter, idir)
    shutil.move(ioctl_onleave, idir)
    shutil.rmtree(ioctl_dir)


def main(raw_seeds_dir: str) -> None:
    test_dirs: List[str] = listdir_abs(raw_seeds_dir)
    out_dir: str = os.path.join(raw_seeds_dir, "out")

    # remove out dir if it already exists
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    # create out dir and process each sequence dir
    os.mkdir(out_dir)
    for idx, test_dir in enumerate(test_dirs):
        if has_callbacks(test_dir):
            merge_callbacks(test_dir)

        seq_dirs: List[str] = listdir_abs(test_dir)
        for seq_dir in seq_dirs:
            interaction_dirs: List[str] = listdir_abs(seq_dir)
            for idir in interaction_dirs:
                rearrange(idir)

            # remove gaps in sequence numbering

            interaction_dirs = sorted(
                [d for d in glob.glob(f"{seq_dir}/*")],
                key=lambda d: int(os.path.basename(d)),
            )

            for dir_idx, idir in enumerate(interaction_dirs):
                dst_dir = os.path.join(os.path.dirname(idir), str(dir_idx))
                shutil.move(idir, dst_dir)

        src = os.path.join(test_dir, "0")
        dst = os.path.join(raw_seeds_dir, "out", str(idx))
        shutil.move(src, dst)
        shutil.rmtree(test_dir)


def usage():
    print(f"Usage:\n\t{sys.argv[0]} <dualrecord_out_dir>")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        usage()
    else:
        main(sys.argv[1])
