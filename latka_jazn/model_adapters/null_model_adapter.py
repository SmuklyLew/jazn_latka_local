from __future__ import annotations
from .base import ModelAdapterRequest, ModelAdapterResponse
from latka_jazn.version import schema_version
class NullModelAdapter:
    name='null_model_adapter'
    def generate(self, request: ModelAdapterRequest) -> ModelAdapterResponse:
        return ModelAdapterResponse(text='', provider='none', model='none', status='requires_external_model_execution')
    def describe(self):
        return {'schema_version':schema_version('null_model_adapter'),'name':self.name,'status':'available_as_truthful_fallback','truth_boundary':'Ten adapter nie udaje modelu. Zwraca pusty wynik i status requires_external_model_execution.'}
