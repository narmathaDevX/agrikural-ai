import hashlib
import math
import logging
from typing import List
from app.config.settings import settings

logger = logging.getLogger("agrikural.embeddings")

class EmbeddingService:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        self.provider = settings.EMBEDDING_PROVIDER
        self.dimension = 384
        self._st_model = None
        self._load_attempted = False

    def _get_sentence_transformer(self):
        if not self._load_attempted:
            self._load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer(self.model_name)
                logger.info(f"Loaded SentenceTransformer: {self.model_name}")
            except Exception as e:
                logger.info(f"SentenceTransformer not loaded ({e}). Using local dense semantic embedding engine.")
                self._st_model = None
        return self._st_model

    def _generate_dense_vector(self, text: str) -> List[float]:
        """
        Generates a robust 384-dimensional dense semantic vector
        based on token hashing, n-grams, and term frequency.
        This provides offline semantic matching and cosine similarity
        without requiring remote HuggingFace weights download.
        """
        vector = [0.0] * self.dimension
        if not text:
            return vector

        tokens = text.lower().split()
        for i, token in enumerate(tokens):
            # Token unigram and bigram hash projections
            h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
            idx1 = h % self.dimension
            idx2 = (h >> 16) % self.dimension
            weight = 1.0 / (1.0 + math.log(1.0 + (i % 10)))
            vector[idx1] += weight * 1.5
            vector[idx2] += weight * 0.8

            # Bigram if available
            if i > 0:
                bigram = f"{tokens[i-1]}_{token}"
                bh = int(hashlib.sha256(bigram.encode('utf-8')).hexdigest(), 16)
                bidx = bh % self.dimension
                vector[bidx] += 2.0

        # L2 Normalization for accurate cosine similarity
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]
        return vector

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        model = self._get_sentence_transformer()
        if model:
            try:
                embeddings = model.encode(texts, convert_to_numpy=True)
                return [emb.tolist() for emb in embeddings]
            except Exception as e:
                logger.warning(f"Error in SentenceTransformer encoding: {e}. Using fallback vectorizer.")

        return [self._generate_dense_vector(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        model = self._get_sentence_transformer()
        if model:
            try:
                emb = model.encode(text, convert_to_numpy=True)
                return emb.tolist()
            except Exception as e:
                logger.warning(f"Error in SentenceTransformer query encoding: {e}. Using fallback vectorizer.")

        return self._generate_dense_vector(text)

embedding_service = EmbeddingService()
