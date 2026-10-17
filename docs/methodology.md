# Implemented methodology

Text is normalized for extraction and compared with TF-IDF character n-grams for lineage candidates. Exact normalized matches, high cosine similarity, shared contact details, and shared application URLs are candidate copied/derived signals; medium similarity remains unknown and requires review. The initial 0.72 threshold is a transparent pilot default, not a final-test-selected threshold; it must be frozen before final testing.

Naive aggregation counts every evidence item. Lineage-aware aggregation counts one item per known dependent group while preserving the original records. Unknown relationships are not silently converted into independence. Decision policy returns contradiction, evidence-supported assessment, unresolved authorization, or abstention. The numerical counts are aggregation diagnostics, not probabilities.
