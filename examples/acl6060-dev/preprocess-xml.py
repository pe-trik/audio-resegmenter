#!/usr/bin/env python3

"""
This script is used to preprocess the ACL 60/60 dev set.
It reads the XML file and saves each document as a separate text file.
"""

from collections import defaultdict
import os
import xml.etree.ElementTree as ET


def load_segments_from_xml(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    docs = defaultdict(dict)
    for d in root.findall('.//doc'):
        docid = d.attrib['docid']
        for s in d.findall('.//seg'):
            segid = s.attrib['id']
            text = s.text
            docs[docid][segid] = text

    return docs


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("xml", type=str, required=True)
    parser.add_argument("save_dir", type=str, required=True)
    args = parser.parse_args()

    docs = load_segments_from_xml(args.xml)

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    for docid, segs in docs.items():
        with open(os.path.join(args.save_dir, docid + ".txt"), "w", encoding="utf-8") as f:
            for segid, text in segs.items():
                f.write(text.strip() + "\n")
