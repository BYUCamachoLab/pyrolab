from pyrolab.api import locate_ns, Proxy

ns = locate_ns(host="localhost")
uri = ns.lookup("test.SampleService")

proxies = []
for i in range(10):
    proxies.append(Proxy(uri))

for i, proxy in enumerate(proxies):
    try:
        print("{} requesting lock".format(i))
        proxy.lock()
        print("{} got lock".format(i))
    except Exception as e:
        print(f"{i} failed to acquire lock")

print('---------')

for i, proxy in enumerate(proxies):
    try:
        print(proxy.echo(f"hello, server from {i}"))
    except Exception as e:
        print(f"{i} failed to echo")
