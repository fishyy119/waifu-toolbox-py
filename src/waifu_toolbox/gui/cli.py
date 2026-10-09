import argparse
from ipaddress import AddressValueError, IPv4Address


def _parse_host(value: str) -> str:
    try:
        address = IPv4Address(value)
    except AddressValueError as error:
        raise argparse.ArgumentTypeError("监听地址必须是有效的 IPv4 地址") from error
    if address.is_unspecified:
        raise argparse.ArgumentTypeError("请指定具体的 IPv4 地址，不能使用 0.0.0.0")
    return str(address)


def main() -> None:
    parser = argparse.ArgumentParser(prog="waifu-gui", description="Waifu Toolbox 本地 Web 界面")
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        type=_parse_host,
        metavar="IP",
        help="追加监听的本机 IPv4 地址，可重复传入，始终监听 127.0.0.1",
    )
    parser.add_argument("--port", type=int, default=3039)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("端口必须位于 1 到 65535 之间")

    from .app import run

    run(additional_hosts=args.host, port=args.port)
