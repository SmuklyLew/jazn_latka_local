from __future__ import annotations
from .base import ModelAdapterRequest, ModelAdapterResponse
class NullModelAdapter:
    name='null_model_adapter'
    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        return ModelAdapterResponse(text='', provider='none', model='none', status='requires_external_model_execution')
    def describe(self):
        return {'schema_version':'null_model_adapter/v14.7.0','name':self.name,'status':'available_as_truthful_fallback','truth_boundary':'Ten adapter nie udaje modelu. Zwraca pusty wynik i status requires_external_model_execution.'}
