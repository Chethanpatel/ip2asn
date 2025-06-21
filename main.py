from fastapi import FastAPI
from fastapi.responses import JSONResponse
import pandas as pd
import ipaddress
from intervaltree import IntervalTree
from urllib.request import Request, urlopen
import os

app = FastAPI()

IP2ASN_URL = "https://iptoasn.com/data/ip2asn-v4.tsv.gz"
IP2ASN_FILENAME = "ip2asn-v4.tsv.gz"

def download_ip2asn():
    if not os.path.exists(IP2ASN_FILENAME):
        req = Request(IP2ASN_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as response, open(IP2ASN_FILENAME, 'wb') as out_file:
            out_file.write(response.read())
    return IP2ASN_FILENAME

def load_ip2asn_interval_tree(filename):
    df = pd.read_csv(
        filename,
        sep="\t",
        compression='gzip',
        names=["range_start", "range_end", "AS_number", "country_code", "AS_description"],
        dtype={"range_start": str, "range_end": str, "AS_number": int, "country_code": str, "AS_description": str}
    )

    tree = IntervalTree()
    for _, row in df.iterrows():
        try:
            start = int(ipaddress.IPv4Address(row["range_start"]))
            end = int(ipaddress.IPv4Address(row["range_end"]))
            tree[start:end+1] = {
                "AS_number": row["AS_number"],
                "country_code": row["country_code"],
                "AS_description": row["AS_description"]
            }
        except Exception:
            continue
    return tree

# Load the tree on startup
filename = download_ip2asn()
ASN_TREE = load_ip2asn_interval_tree(filename)

@app.get("/getasn/{ip}")
def get_asn(ip: str):
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        if ip_obj.is_private:
            return JSONResponse({"AS_description": "Private Network"})
        ip_int = int(ip_obj)
    except Exception:
        return JSONResponse({"AS_description": "Invalid IP"})

    matches = ASN_TREE[ip_int]
    if matches:
        match = list(matches)[0].data
        return JSONResponse({
            "AS_number": match["AS_number"],
            "country_code": match["country_code"],
            "AS_description": match["AS_description"]
        })
    return JSONResponse({"AS_description": "ASN Unknown"})
