# Eyes Project AI

Pipeline de visão computacional do Eyes Project para avaliação, adaptação e
exportação de modelos de detecção de objetos para dispositivos móveis.

## Protocolo do MVP

O escopo científico inicial está aprovado e versionado em:

- [protocolo experimental](docs/experiment-protocol.md);
- [guia de anotação](docs/annotation-guide.md);
- [privacidade e governança](docs/privacy-and-data-governance.md);
- [ADR do baseline pré-treinado](docs/adr/0001-pretrained-efficientdet-lite0-baseline.md);
- [contrato executável do modelo](docs/model-contract.md);
- [configuração normativa legível por máquina](config/experiment.v1.json).

A primeira demonstração usa EfficientDet-Lite0 pré-treinado e não exige treino.
Ela habilita pessoa, cadeira, mesa/carteira como hipótese de mapeamento e mochila.
Porta permanece definida, mas depende de dataset/modelo customizado.

Valide o protocolo antes de qualquer experimento:

```powershell
py -3.11 -m uv run python -m eyes_project_ai.protocol
```

O protocolo usa o POCO X5 Pro 5G como aparelho físico de referência. A REN-36
fixou origem, SHA-256, licença, labels e contrato de tensores do artefato. O
benchmark permanece `blocked` somente até capturar o inventário real da unidade
(Android, RAM, build, versão do app, commit, bateria e estado térmico). Métricas
observadas nunca devem ser gravadas como se fossem configuração pré-experimental.

## Modelo pré-treinado

O MVP **não treina um modelo do zero**. Ele usa o EfficientDet-Lite0 oficial,
pré-treinado no COCO 2017, e executa localmente. O binário fica fora do Git e é
adquirido de forma reprodutível:

```powershell
py -3.11 -m uv run python -m eyes_project_ai.acquire_model
py -3.11 -m uv run python -m eyes_project_ai.inspect_model
```

O manifesto [`config/model-manifest.v1.json`](config/model-manifest.v1.json)
fixa URL, tamanho, SHA-256, Apache-2.0, entrada, saídas e índices de classe. O
download é atômico e falha fechado: bytes ou labels divergentes não são usados.

Para uma imagem local, o runner de referência permite comparar a implementação
Mobile sem transformar Python em serviço por frame:

```powershell
py -3.11 -m uv run python -m eyes_project_ai.tflite_runner imagem.jpg
```

## Toolchain fixado

- Python `3.11`, declarado em `.python-version` e `pyproject.toml`;
- uv `0.12.5` para ambiente virtual e resolução de dependências;
- dependências exatas registradas em `uv.lock`.

Treinamento e exportação customizada são condicionais aos resultados do
baseline. Python é tooling e referência; a inferência crítica do app permanece
on-device e offline.

## Configuração no Windows

```powershell
py -3.11 -m pip install --user uv==0.12.5
py -3.11 -m uv sync --locked --all-groups
./scripts/check-toolchain.ps1
```

O uv cria o ambiente `.venv` automaticamente. Não instale dependências do
projeto globalmente e não edite `uv.lock` à mão.

## Qualidade

```powershell
py -3.11 -m uv run ruff check .
py -3.11 -m uv run pytest
py -3.11 -m uv run python -m eyes_project_ai.inspect_model
```

Dependências novas devem ser incluídas com `uv add` ou `uv add --dev`, seguidas
de revisão do `pyproject.toml` e do `uv.lock` no mesmo Pull Request.

## Privacidade

Datasets, imagens, modelos e resultados locais ficam fora do Git por padrão.
Somente artefatos aprovados, com origem e licença documentadas, poderão ser
versionados nos cards de IA correspondentes.

## Fluxo Git

As funcionalidades partem de `dev`, usam `feat/<linear-id>-<nome-curto>` e
retornam por Pull Request. A promoção para produção ocorre de `dev` para
`main`, que permanece protegida.
