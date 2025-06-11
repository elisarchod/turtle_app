import qbittorrentapi

# instantiate a Client using the appropriate WebUI configuration
conn_info = dict(host="192.168.1.205", port=15080, username="admin", password="adminadmin", )
qbt_client = qbittorrentapi.Client(**conn_info)
qbt_client

for torrent in qbt_client.torrents_info():
    print(f"{torrent.hash[-6:]}: {torrent.name} ({torrent.state})")



qbt_client.search_install_plugin('https://gist.githubusercontent.com/scadams/56635407b8dfb8f5f7ede6873922ac8b/raw/f654c10468a0b9945bec9bf31e216993c9b7a961/one337x.py')

qbt_client.search_enable_plugin('one337x')
qbt_client.search_plugins()


qbt_client.search_start("asdasd", plugins=['all'])