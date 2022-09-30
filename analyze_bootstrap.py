import argparse
from collections import Counter
import nano
from pprint import pprint


def count_distinct(list):
    c = dict(Counter(list))
    return c


def extract_subtype(block_info):
    block = block_info["contents"]
    subtype = block_info["subtype"] if ("subtype" in block_info) else block["type"]
    return subtype


def extract_source(block):
    source = block["link"] if (block["type"] == "state") else block["source"]
    return source


def try_find_block(rpc, hash):
    try:
        return rpc.block(hash)
    except:
        return None


def main(client_rpc_addr, server_rpc_addr):
    client_rpc = nano.rpc.Client(client_rpc_addr)
    server_rpc = nano.rpc.Client(server_rpc_addr)

    print("client blocks:", client_rpc.block_count())
    print("server blocks:", server_rpc.block_count())

    ascending_info = client_rpc.call(action="backoffs")
    backoffs = ascending_info["backoffs"]
    blocking = ascending_info["blocking"]
    forwarding = ascending_info["forwarding"]

    print(
        "backoffs:",
        len(backoffs),
        "blocking:",
        len(blocking),
        "forwarding:",
        len(forwarding),
    )

    # pprint(ascending_info)

    ledger = client_rpc.call(action="ledger")

    types_aggr = []

    for account, info in ledger["accounts"].items():
        frontier = info["frontier"]
        # print (account, frontier)

        successors = server_rpc.successors(block=frontier, count=2)
        assert successors[0] == frontier

        successor_hash = successors[1] if len(successors) >= 2 else None
        # print (account, frontier, successor_hash)

        if successor_hash:
            successor_info = server_rpc.call(
                action="block_info", params={"hash": successor_hash, "json_block": True}
            )
            successor_block = successor_info["contents"]

            pprint("missing successor: ", successor_hash)

            subtype = extract_subtype(successor_info)
            types_aggr.append(subtype)

            # print(subtype)

            source = extract_source(successor_block)
            source_found = try_find_block(client_rpc, source)

            # print(source_found, found)

            if source_found:
                # source block found already in ledger but not proceeding hmm

                account_in_blocking = account in blocking
                account_in_backoffs = account in backoffs
                print(
                    "source problem:",
                    "blocking:",
                    account_in_blocking,
                    "backoffs:",
                    account_in_backoffs,
                )

                pass

            pass

    print("types:", count_distinct(types_aggr))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client_rpc", type=str, required=True)
    parser.add_argument("--server_rpc", type=str, required=True)
    args = parser.parse_args()

    main(args.client_rpc, args.server_rpc)
