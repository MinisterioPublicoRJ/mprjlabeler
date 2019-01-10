from django.db import models


SITUACOES_FILTRO = (
    (1, 'Em Criação'),
    (2, 'Baixando Documentos'),
    (3, 'Executando Filtros'),
    (4, 'Documentos Classificados'),
    (5, 'Compactando'),
    (6, 'Download Disponível')
)

TIPOS_FILTRO = (
    (1, 'Expressão Principal'),
    (2, 'Expressão Reforço'),
    (3, 'Termos de Exclusão'),
    (4, 'Termos de Invalidação'),
    (5, 'Termos de Reforço'),
)


class TipoMovimento(models.Model):
    nome = models.CharField(max_length=50)
    nome_tj = models.CharField(max_length=50)


class Filtro(models.Model):
    nome = models.CharField(max_length=50)
    tipos_movimento = models.ManyToManyField('TipoMovimento')
    arquivo_documentos = models.FileField(null=True, blank=True)
    situacao = models.CharField(max_length=1, choices=SITUACOES_FILTRO)
    saida = models.FileField(null=True, blank=True)


class ClasseFiltro(models.Model):
    filtro = models.ForeignKey('Filtro', on_delete=models.CASCADE)
    nome = models.CharField(max_length=50)
    ordem = models.IntegerField()


class ItemFiltro(models.Model):
    classe_filtro = models.ForeignKey('ClasseFiltro', on_delete=models.CASCADE)
    termos = models.CharField(max_length=255)
    tipo = models.CharField(max_length=1, choices=TIPOS_FILTRO)


class Documento(models.Model):
    filtro = models.ForeignKey('ClasseFiltro', blank=True, null=True, on_delete=models.CASCADE)
    numero = models.CharField(max_length=32)
    tipo_movimento = models.ForeignKey('TipoMovimento', on_delete=models.CASCADE)
    conteudo = models.TextField()