import streamlit as st
import pandas as pd
import ipaddress
import json
from intervaltree import IntervalTree
from urllib.request import Request, urlopen
import os

# Constants
IP2ASN_URL = "https://iptoasn.com/data/ip2asn-v4.tsv.gz"
IP2ASN_FILENAME = "ip2asn-v4.tsv.gz"

# Download the IP2ASN dataset
@st.cache_data(ttl=86400)  # cache for 1 day
def download_ip2asn():
    if not os.path.exists(IP2ASN_FILENAME):
        req = Request(IP2ASN_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req) as response, open(IP2ASN_FILENAME, 'wb') as out_file:
            out_file.write(response.read())
    return IP2ASN_FILENAME

# Load the data into an interval tree
@st.cache_resource
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
            tree[start:end + 1] = {
                "AS_number": row["AS_number"],
                "country_code": row["country_code"],
                "AS_description": row["AS_description"]
            }
        except Exception:
            continue
    return tree

# IP lookup function
def get_asn_info(ip, tree):
    try:
        ip_obj = ipaddress.IPv4Address(ip)
        if ip_obj.is_private:
            return {"AS_description": "Private Network"}
        ip_int = int(ip_obj)
    except Exception:
        return {"AS_description": "Invalid IP"}

    matches = tree[ip_int]
    if matches:
        match = list(matches)[0].data
        return {
            "AS_number": match["AS_number"],
            "country_code": match["country_code"],
            "AS_description": match["AS_description"]
        }
    return {"AS_description": "ASN Unknown"}

# ----------------- Streamlit Interface -----------------

filename = download_ip2asn()
tree = load_ip2asn_interval_tree(filename)

# Check if query param is passed
query_params = st.experimental_get_query_params()
ip_param = query_params.get("ip", [None])[0]

if ip_param:
    # API-style response
    result = get_asn_info(ip_param.strip(), tree)
    st.markdown("```json\n" + json.dumps(result, indent=2) + "\n```")
else:
    # UI mode
    st.title("🔍 IP to ASN Lookup")
    ip_input = st.text_input("Enter an IPv4 Address (e.g. 8.8.8.8)", "")
    if st.button("Get ASN Info") and ip_input:
        result = get_asn_info(ip_input.strip(), tree)
        st.subheader("Result")
        st.json(result)
