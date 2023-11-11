from fuzz.utils import p8


class TEEZZ_CMD(object):
    """Command IDs to communicate with executor on the target."""

    TEEZZ_CMD_START = p8(0x01)
    TEEZZ_CMD_SEND = p8(0x02)
    TEEZZ_CMD_END = p8(0x03)
    TEEZZ_CMD_TERMINATE = p8(0x04)


class TEEID(object):
    """Unique identifiers for the different target TEEs."""

    TC = "tc"
    QSEE = "qsee"
    OPTEE = "optee"
    BEANPOD = "beanpod"


TEEID_dict = {
    getattr(TEEID, k): k
    for k in dir(TEEID)
    if not callable(getattr(TEEID, k)) and not k.startswith("__")
}
