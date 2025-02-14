from typing import Optional

from core.model_runtime.entities.model_entities import PriceType
from core.model_runtime.entities.text_embedding_entities import TextEmbeddingResult, EmbeddingUsage
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.text_embedding_model import TextEmbeddingModel
from core.model_runtime.errors.invoke import InvokeError, InvokeConnectionError, InvokeServerUnavailableError, \
    InvokeRateLimitError, InvokeAuthorizationError, InvokeBadRequestError

from requests import post
from json import dumps, JSONDecodeError
from os.path import join

import time

class LocalAITextEmbeddingModel(TextEmbeddingModel):
    """
    Model class for Jina text embedding model.
    """
    def _invoke(self, model: str, credentials: dict,
                texts: list[str], user: Optional[str] = None) \
            -> TextEmbeddingResult:
        """
        Invoke text embedding model

        :param model: model name
        :param credentials: model credentials
        :param texts: texts to embed
        :param user: unique user id
        :return: embeddings result
        """
        if len(texts) != 1:
            raise InvokeBadRequestError('Only one text is supported')

        server_url = credentials['server_url']
        model_name = model
        if not server_url:
            raise CredentialsValidateFailedError('server_url is required')
        if not model_name:
            raise CredentialsValidateFailedError('model_name is required')
        
        url = server_url
        headers = {
            'Authorization': 'Bearer 123',
            'Content-Type': 'application/json'
        }

        data = {
            'model': model_name,
            'input': texts[0]
        }

        try:
            response = post(join(url, 'embeddings'), headers=headers, data=dumps(data), timeout=10)
        except Exception as e:
            raise InvokeConnectionError(e)
        
        if response.status_code != 200:
            try:
                resp = response.json()
                code = resp['error']['code']
                msg = resp['error']['message']
                if code == 500:
                    raise InvokeServerUnavailableError(msg)
                
                if response.status_code == 401:
                    raise InvokeAuthorizationError(msg)
                elif response.status_code == 429:
                    raise InvokeRateLimitError(msg)
                elif response.status_code == 500:
                    raise InvokeServerUnavailableError(msg)
                else:
                    raise InvokeError(msg)
            except JSONDecodeError as e:
                raise InvokeServerUnavailableError(f"Failed to convert response to json: {e} with text: {response.text}")

        try:
            resp = response.json()
            embeddings = resp['data']
            usage = resp['usage']
        except Exception as e:
            raise InvokeServerUnavailableError(f"Failed to convert response to json: {e} with text: {response.text}")

        usage = self._calc_response_usage(model=model, credentials=credentials, tokens=usage['total_tokens'])

        result = TextEmbeddingResult(
            model=model,
            embeddings=[[
                float(data) for data in x['embedding']
            ] for x in embeddings],
            usage=usage
        )

        return result

    def get_num_tokens(self, model: str, credentials: dict, texts: list[str]) -> int:
        """
        Get number of tokens for given prompt messages

        :param model: model name
        :param credentials: model credentials
        :param texts: texts to embed
        :return:
        """
        num_tokens = 0
        for text in texts:
            # use GPT2Tokenizer to get num tokens
            num_tokens += self._get_num_tokens_by_gpt2(text)
        return num_tokens

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            self._invoke(model=model, credentials=credentials, texts=['ping'])
        except InvokeAuthorizationError:
            raise CredentialsValidateFailedError('Invalid credentials')
        except InvokeConnectionError as e:
            raise CredentialsValidateFailedError(f'Invalid credentials: {e}')

    @property
    def _invoke_error_mapping(self) -> dict[type[InvokeError], list[type[Exception]]]:
        return {
            InvokeConnectionError: [
                InvokeConnectionError
            ],
            InvokeServerUnavailableError: [
                InvokeServerUnavailableError
            ],
            InvokeRateLimitError: [
                InvokeRateLimitError
            ],
            InvokeAuthorizationError: [
                InvokeAuthorizationError
            ],
            InvokeBadRequestError: [
                KeyError
            ]
        }
    
    def _calc_response_usage(self, model: str, credentials: dict, tokens: int) -> EmbeddingUsage:
        """
        Calculate response usage

        :param model: model name
        :param credentials: model credentials
        :param tokens: input tokens
        :return: usage
        """
        # get input price info
        input_price_info = self.get_price(
            model=model,
            credentials=credentials,
            price_type=PriceType.INPUT,
            tokens=tokens
        )

        # transform usage
        usage = EmbeddingUsage(
            tokens=tokens,
            total_tokens=tokens,
            unit_price=input_price_info.unit_price,
            price_unit=input_price_info.unit,
            total_price=input_price_info.total_amount,
            currency=input_price_info.currency,
            latency=time.perf_counter() - self.started_at
        )

        return usage
