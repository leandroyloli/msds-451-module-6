# Historical collection source

`holdings_v2.py` preserves the exploratory source that retrieved and normalized the original holdings. It is not called by `run.py`; its original paths were not adapted to imply a new collection.

The process consulted issuer pages, complete CSV/JSON/XLSX files, public CVM records and normalization intermediates. It cross-matched security identifiers to complete classifications and documented remaining gaps. Exploratory steps created stage files, HTML and JavaScript in the original workspace. This single file does not promise to reconstruct the entire collection or obtain a new online snapshot.

The 46 raw files referenced by the final manifest are in `../../data/holdings/`, with verified copy hashes. That folder's manifest records sources and transformations. Frozen normalized inputs suffice to rerun the study offline without the original workspace.

Original collection location: `C:/studing/msds-451-module-6/pipeline/holdings_v2.py` before folder relocation. Portuguese strings in the collector are source field names/classification tokens required to parse authentic CVM records, not untranslated interface prose.
