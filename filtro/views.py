import os
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.db import connection
from django.utils.encoding import smart_str
from django.http import JsonResponse, StreamingHttpResponse
from wsgiref.util import FileWrapper
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .forms import (
    AdicionarFiltroForm,
    FiltroForm,
    AdicionarClasseForm,
    ItemFiltroForm,
)
from .models import (
    Filtro,
    ClasseFiltro,
    ItemFiltro
)
from .tasks import (
    submeter_classificacao,
    compactar,
)


def obter_filtro(idfiltro, username):
    return get_object_or_404(
        Filtro,
        pk=idfiltro,
        responsavel=username)


def obter_filtros(username):
    return Filtro.objects.filter(
        responsavel=username
    )


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


@login_required
def filtros(request):
    novo_filtro_form = AdicionarFiltroForm

    return render(
        request,
        'filtro/filtros.html',
        {
            'filtros': obter_filtros(request.user.username),
            'novofiltroform': novo_filtro_form
        }
    )


def obter_contadores_filtro(filtro):
    query = """select
        case when filtro_classefiltro.nome is null then 'Sem Classificação'
        else filtro_classefiltro.nome end nomeclasse,
        classe,
        count(classe) total
        from (
        SELECT
        case when classe_filtro_id is null then 0
        else classe_filtro_id end classe
        FROM filtro_documento
        WHERE "filtro_documento"."filtro_id" = %s) tabela
        left join filtro_classefiltro on
        tabela.classe = filtro_classefiltro.id
        GROUP BY nomeclasse, classe
        ORDER BY "total" desc"""

    with connection.cursor() as cursor:
        cursor.execute(query, [filtro.id])
        return dictfetchall(cursor)


@login_required
@require_http_methods(['POST'])
def adicionar_filtro(request):
    form = AdicionarFiltroForm(request.POST)
    form.instance.responsavel = request.user.username

    form.save()

    messages.success(
        request,
        "Filtro %s adicionado e salvo" % form.instance.nome)

    return redirect(
        reverse(
            'filtros-filtro',
            args=[form.instance.id]
        )
    )


@login_required
def filtro(request, idfiltro):
    m_filtro = obter_filtro(idfiltro, request.user.username)
    form = FiltroForm(instance=m_filtro)

    if request.method == 'POST':
        form = FiltroForm(
            request.POST,
            request.FILES,
            instance=m_filtro
        )
        form.is_valid()
        form.save()

        messages.success(request, "Filtro salvo!")

    return render(
        request,
        'filtro/filtro.html',
        {
            'form': form,
            'model': m_filtro,
            'idfiltro': idfiltro,
            'adicionarclasseform': AdicionarClasseForm(),
            'itemfiltroform': ItemFiltroForm(),
        }
    )


@login_required
@require_http_methods(['POST'])
def excuir_filtro(request):
    idfiltro = request.POST.get('idfiltro')

    m_filtro = obter_filtro(idfiltro, request.user.username)
    m_filtro.delete()

    messages.success(request, 'Filtro removido com Sucesso!')
    return redirect(
        reverse(
            'filtros',
        )
    )


@login_required
@require_http_methods(['POST'])
def adicionar_classe(request, idfiltro):
    f_adicionar = AdicionarClasseForm(request.POST)

    if not f_adicionar.is_valid():
        return None

    if f_adicionar.cleaned_data['idclasse']:
        f_adicionar = AdicionarClasseForm(
            request.POST,
            instance=get_object_or_404(
                ClasseFiltro,
                pk=f_adicionar.cleaned_data['idclasse'])
        )

        f_adicionar.save()
        messages.success(request, 'Classe de Filtro alterada com sucesso!')
    else:
        m_filtro = obter_filtro(idfiltro, request.user.username)

        f_adicionar.instance.filtro = m_filtro
        f_adicionar.instance.ordem = len(m_filtro.classefiltro_set.all())
        f_adicionar.save()

        messages.success(request, 'Classe de Filtro adicionada!')

    return redirect(
        reverse(
            'filtros-filtro',
            args=[idfiltro]
        )
    )


@login_required
@require_http_methods(['POST'])
def excluir_classe(request, idfiltro, idclasse):
    m_classe = get_object_or_404(
        ClasseFiltro,
        pk=idclasse,
        filtro__id=idfiltro
    )

    m_classe.delete()

    messages.warning(request, 'Classe de filtro removida')

    return redirect(
            reverse(
                'filtros-filtro',
                args=[idfiltro]
            )
        )


@login_required
@require_http_methods(['GET'])
def mover_classe(request, idfiltro, idclasse, direcao):
    m_classe = get_object_or_404(
        ClasseFiltro,
        pk=idclasse,
        filtro__id=idfiltro)

    if direcao == 'acima':
        m_classe.up()

    else:
        m_classe.down()

    messages.success(request, 'Classe movida %s!' % direcao)

    return redirect(
        reverse(
            'filtros-filtro',
            args=[idfiltro]
        )
    )


@login_required
@require_http_methods(['POST'])
def adicionar_itemfiltro(request):
    f_itemfiltro = ItemFiltroForm(request.POST)

    if f_itemfiltro.is_valid():
        if f_itemfiltro.cleaned_data['iditemfiltro']:
            m_itemfiltro = get_object_or_404(
                ItemFiltro,
                pk=f_itemfiltro.cleaned_data['iditemfiltro']
            )

            f_itemfiltro = ItemFiltroForm(
                request.POST,
                instance=m_itemfiltro)

            f_itemfiltro.save()

            messages.success(request, 'Item de Filtro alterado!')
        else:
            f_itemfiltro.instance.classe_filtro = get_object_or_404(
                ClasseFiltro,
                pk=f_itemfiltro.cleaned_data['idclasse'])

            f_itemfiltro.save()

            messages.success(request, 'Item de Filtro adicionado!')

    return redirect(
        reverse(
            'filtros-filtro',
            args=[f_itemfiltro.cleaned_data['idfiltro']]
        )
    )


@login_required
@require_http_methods(['GET'])
def excluir_item_filtro(request, idfiltro, iditemfiltro):
    m_itemfiltro = get_object_or_404(ItemFiltro, pk=iditemfiltro)

    m_itemfiltro.delete()

    messages.warning(request, 'Item de Filtro removido com sucesso!')

    return redirect(
        reverse(
            'filtros-filtro',
            args=[idfiltro]
        )
    )


@login_required
@require_http_methods(['GET'])
def classificar(request, idfiltro):
    submeter_classificacao.delay(idfiltro)

    messages.info(
        request,
        ('Filtro submetido para classificação! Acompanhe o '
         'andamento pela tela de gestão dos filtros.')
    )

    return redirect(
        reverse(
            'filtros'
        )
    )


@login_required
@require_http_methods(['GET'])
def obter_situacao(request, idfiltro):
    m_filtro = obter_filtro(idfiltro, request.user.username)

    return JsonResponse(
        {
            'situacao': m_filtro.situacao,
            'percentual': m_filtro.percentual_atual,
            'descricao': m_filtro.get_situacao_display(),
            'disponivel': m_filtro.saida.url if m_filtro.saida.name else None
        }
    )


@login_required
@require_http_methods(['GET'])
def listar_resultados(request, idfiltro):
    m_filtro = obter_filtro(idfiltro, request.user.username)

    classe = request.GET.get('classe', 'T')

    sumario = m_filtro.documento_set.all().values(
        'classe_filtro__nome').annotate(
        total=Count('classe_filtro__nome')).order_by(
        '-total')

    documentos = m_filtro.documento_set

    sumario = obter_contadores_filtro(m_filtro)

    total_classificados = documentos.all().exclude(
        classe_filtro=None).count()
    total_documentos = documentos.all().count()

    for item in sumario:
        item['percentual_classe'] = (item['total'] * 100.0)/total_classificados
        item['percentual_total'] = (item['total'] * 100.0)/total_documentos

    if classe == 'T':
        documentos = documentos.all()
    elif classe == '0':
        documentos = documentos.filter(classe_filtro__isnull=True)
    else:
        documentos = documentos.filter(classe_filtro=classe).all()

    total = documentos.count()
    paginator = Paginator(documentos, 25)

    page = request.GET.get('page', 1)
    documentos = paginator.get_page(page)

    return render(
        request,
        'filtro/resultados.html',
        {
            'documentos': documentos,
            'filtro': m_filtro,
            'sumario': sumario,
            'total_classificados': total_classificados,
            'total_documentos': total_documentos,
            'total': total,
            'classe': classe
        }
    )


@login_required
@require_http_methods(['GET'])
def executar_compactacao(request, idfiltro):
    compactar.delay(idfiltro)

    messages.info(
        request,
        ('Filtro submetido para compactação! Acompanhe o '
         'andamento pela tela de gestão dos filtros.')
    )

    return redirect(
        reverse(
            'filtros'
        )
    )


@login_required
@require_http_methods(['GET'])
def mediaview(request, mediafile):
    del request
    fullfile = os.path.join(settings.MEDIA_ROOT, mediafile)
    response = StreamingHttpResponse(
        FileWrapper(open(fullfile, 'rb'), 8192)
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % mediafile
    response['X-Sendfile'] = smart_str(fullfile)
    return response
