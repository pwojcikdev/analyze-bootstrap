import argparse
from collections import Counter
import nano
from pprint import pprint
from tqdm import tqdm


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


def try_find_account_info(rpc, account):
    try:
        return rpc.account_info(account)
    except:
        return None


def try_find_successor(rpc, hash):
    successors = server_rpc.successors(block=hash, count=2)
    assert successors[0] == hash
    successor_hash = successors[1] if len(successors) >= 2 else None
    return successor_hash


def analyze_priorities():
    for account in priorities:
        print()

        print("priority:", account)

        server_account_info = try_find_account_info(server_rpc, account)
        client_account_info = try_find_account_info(client_rpc, account)

        if server_account_info is None:
            missing_account = client_account_info is None

            print("account does not exist on server !!!")
            print(
                "missing",
                "|",
                "client account:",
                missing_account,
            )
        else:
            print("info:", server_account_info)

            client_open = try_find_block(client_rpc, server_account_info["open_block"])
            missing_open = client_open is None
            missing_account = client_account_info is None

            print(
                "missing",
                "|",
                "open:",
                missing_open,
                "|",
                "account:",
                missing_account,
            )


def analyze_blocking():
    types_aggr = []

    for account in tqdm(blocking):
        # print()
        # print("blocking:", account)

        def find_blocking(account):
            client_account_info = try_find_account_info(client_rpc, account)

            if client_account_info is None:
                server_account_info = server_rpc.account_info(account)
                open_hash = server_account_info["open_block"]
                return open_hash
            else:
                client_frontier = client_account_info["frontier"]
                server_successor = try_find_successor(server_rpc, client_frontier)
                return server_successor

        blocking_hash = find_blocking(account)

        if blocking_hash is None:
            print("unknown blocking !!!")
        else:
            # print("blocking:", blocking_hash)

            blocking_info = server_rpc.call(
                action="block_info",
                params={"hash": blocking_hash, "json_block": True},
            )
            blocking_block = blocking_info["contents"]

            subtype = extract_subtype(blocking_info)

            # print("type:", subtype)
            types_aggr.append(subtype)

            source = extract_source(blocking_block)
            source_found = try_find_block(client_rpc, source)

            if source_found:
                print("source found:", source)

            pass

    print("types:", count_distinct(types_aggr))

    pass


def analyze_ledger():
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
            print()

            successor_info = server_rpc.call(
                action="block_info",
                params={"hash": successor_hash, "json_block": True},
            )
            successor_block = successor_info["contents"]

            print("missing successor: ", successor_hash)

            subtype = extract_subtype(successor_info)
            types_aggr.append(subtype)

            print("type:", subtype)

            def analyze_account():
                print("account:", account)

                account_in_blocking = account in blocking
                account_in_priorities = account in priorities

                print(
                    "account in:",
                    "blocking:",
                    account_in_blocking,
                    "|",
                    "priorities:",
                    account_in_priorities,
                )

            analyze_account()

            def analyze_receive():
                source = extract_source(successor_block)
                source_found = try_find_block(client_rpc, source)

                # print(source_found, found)

                if source_found:
                    # source block found already in ledger but not proceeding hmm

                    account_in_blocking = account in blocking
                    account_in_priorities = account in priorities
                    print(
                        "source problem:",
                        "blocking:",
                        account_in_blocking,
                        "priorities:",
                        account_in_priorities,
                    )

            pass

    print("types:", count_distinct(types_aggr))


def analyze_compare(account):
    print("compare:", account)
    server_account_info = try_find_account_info(server_rpc, account)
    client_account_info = try_find_account_info(client_rpc, account)

    print("client:", client_account_info)
    print("server:", server_account_info)

    account_in_blocking = account in blocking
    account_in_priorities = account in priorities
    print(
        "account in:",
        "blocking:",
        account_in_blocking,
        "|",
        "priorities:",
        account_in_priorities,
    )

    if account_in_priorities:
        # print("priority:", priorities[account])
        pprint(priorities[account])

    open_block = try_find_block(server_rpc, server_account_info["open_block"])
    open_source = extract_source(open_block)

    client_source_block = try_find_block(client_rpc, open_source)
    print("client source block:", client_source_block)

    pass


def main(client_rpc_addr, server_rpc_addr):
    global client_rpc
    global server_rpc
    client_rpc = nano.rpc.Client(client_rpc_addr)
    server_rpc = nano.rpc.Client(server_rpc_addr)

    print("client blocks:", client_rpc.block_count())
    print("server blocks:", server_rpc.block_count())

    global backoff_info
    global priorities
    global blocking
    global tags
    backoff_info = client_rpc.call(action="backoff_info")
    priorities = backoff_info["accounts"]["priorities"]
    blocking = backoff_info["accounts"]["blocking"]
    tags = backoff_info["tags"]

    print(
        "priorities:",
        len(priorities),
        "blocking:",
        len(blocking),
    )

    # pprint(backoff_info)
    pprint(priorities)
    pprint(tags)

    # analyze_priorities()
    # analyze_blocking()
    # analyze_ledger()

    analyze_compare("nano_17zztxtdkbwi5egc7f9bstppjfic6aerixe69n9tc8euyhorbjenp5qse3eb")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", type=str, required=True)
    parser.add_argument("--server", type=str, required=True)
    args = parser.parse_args()

    main(args.client, args.server)
