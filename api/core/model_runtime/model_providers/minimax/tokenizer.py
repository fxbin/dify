from transformers import GPT2Tokenizer
from os.path import join, abspath, dirname
from typing import Any

tokenizer = None

class MinimaxTokenizer:
    @staticmethod
    def _get_num_tokens_by_gpt2(text: str) -> int:
        """
            use gpt2 tokenizer to get num tokens
        """
        tokenizer = MinimaxTokenizer.get_encoder()
        tokens = tokenizer.encode(text)
        return len(tokens)
    
    @staticmethod
    def get_num_tokens(text: str) -> int:
        return MinimaxTokenizer._get_num_tokens_by_gpt2(text)
    
    @staticmethod
    def get_encoder() -> Any:
        global tokenizer

        if tokenizer is None:
            base_path = abspath(__file__)
            gpt2_tokenizer_path = join(dirname(base_path), '..', '__base', 'tokenizers', 'gpt2')
            tokenizer = GPT2Tokenizer.from_pretrained(gpt2_tokenizer_path)

        return tokenizer