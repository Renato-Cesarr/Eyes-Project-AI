# Protocolo experimental do MVP de visão computacional

- **ID:** `eyes-mvp-object-detection-v1`
- **Versão do esquema:** 1
- **Status:** aprovado — execução bloqueada até o manifesto do modelo e o inventário de runtime
- **Linear:** REN-33
- **Última revisão:** 19 de agosto de 2026
- **Configuração normativa:** [`config/experiment.v1.json`](../config/experiment.v1.json)

## 1. Objetivo e limite da evidência

Este protocolo verifica se um detector leve, pré-treinado e executado no
aparelho consegue sustentar uma **demonstração técnica inicial** do Eyes Project
em sala de aula. Ele não certifica o aplicativo como auxílio de mobilidade, não
substitui bengala, cão-guia ou orientação humana e não permite apresentar metas
como resultados antes da execução.

Resultados devem ser publicados em artefato separado, identificando versão do
modelo, hash, commit, aparelho, configuração e conjunto de teste. Este documento
permanece pré-experimental: todos os campos `measured_value` são nulos.

## 2. Estratégia do primeiro incremento

O baseline será o **EfficientDet-Lite0 pré-treinado em COCO 2017**, distribuído
em TensorFlow Lite e desenhado para dispositivos móveis. A escolha reduz o
primeiro incremento a aquisição, verificação e integração de um artefato já
treinado; nenhuma coleta ou sessão de treinamento é necessária para colocar a
primeira inferência no aparelho.

O artefato só poderá ser incorporado ao aplicativo depois que o REN-36 registrar:

1. URL exata e data da aquisição;
2. SHA-256 do arquivo;
3. licença e obrigações de redistribuição verificadas;
4. assinatura dos tensores, metadados e labels;
5. paridade entre o script de referência e o runtime mobile.

YOLOv8n deixa de ser o baseline obrigatório. Ele permanece candidato de
comparação ou fine-tuning, condicionado à necessidade técnica e a uma decisão
explícita sobre a licença AGPL-3.0 ou licença comercial. Essa decisão evita
acoplar todos os repositórios a uma obrigação de licença antes de medir se o
modelo pré-treinado mais simples atende ao TCC.

## 3. Classes fechadas

| Classe de domínio | Fala pt-BR | COCO | Baseline | Prioridade | Observação |
|---|---|---:|---|---|---|
| `person` | pessoa | 0 | habilitada | crítica | Não identifica nem reconhece a pessoa. |
| `chair` | cadeira | 56 | habilitada | alta | Bancos e sofás ficam fora. |
| `table_desk` | mesa | 60 (`dining table`) | habilitada como hipótese | alta | A transferência para carteiras escolares precisa ser medida. |
| `backpack` | mochila | 24 | habilitada | média | Bolsas, malas e estojos ficam fora. |
| `door` | porta | inexistente | desabilitada | alta | Exige dataset e novo modelo; a taxonomia já está definida. |

A versão simples anuncia somente as quatro classes habilitadas. `door` não pode
ser simulada por outra classe nem incluída por regra heurística. Se a equipe
confirmar porta como requisito obrigatório, o gatilho de fine-tuning é acionado.

O [guia de anotação](annotation-guide.md) é normativo para ambiguidades,
oclusão, truncamento e objetos exibidos em telas ou imagens.

## 4. Pergunta, hipóteses e gates

### 4.1 Pergunta

Um EfficientDet-Lite0 pré-treinado consegue reconhecer as quatro classes
habilitadas e produzir eventos com latência suficiente para uma demonstração
local no aparelho Android de referência?

### 4.2 Hipóteses registradas antes do teste

- H1: `person`, `chair` e `backpack` transferem do COCO para a sala de aula sem
  treinamento adicional no nível mínimo da demonstração.
- H2: `dining table` pode representar `table_desk`, mas terá maior risco de
  perda de recall em carteiras escolares.
- H3: inferência local e backpressure mantêm o evento ponta a ponta abaixo do
  gate preliminar sem fila crescente.
- H4: `door` não será detectável de forma confiável pelo baseline.

### 4.3 Gate da demonstração técnica

| Métrica | Gate inicial | Escopo |
|---|---:|---|
| Precision | ≥ 0,60 | por classe habilitada e macro, IoU ≥ 0,50 |
| Recall | ≥ 0,60 | por classe habilitada e macro, IoU ≥ 0,50 |
| mAP@0,50 | ≥ 0,50 | macro das classes habilitadas |
| Latência de inferência p95 | ≤ 250 ms | após aquecimento, aparelho físico |
| Latência frame → evento p95 | ≤ 500 ms | não confundir com início/fim da fala |
| Alertas falsos | ≤ 1,0/min | por cenário e total |
| Alertas perdidos | ≤ 0,40 | eventos relevantes anotados |

Esses números são **critérios de engenharia propostos**, não resultados. Passar
o gate autoriza somente a demonstração controlada. Falhar não será ocultado:
aciona ajuste de threshold, mudança de baseline ou dataset/fine-tuning conforme
a causa observada.

## 5. Dados e prevenção de vazamento

### 5.1 Unidade de separação

O split é 70% treino, 15% validação e 15% teste, com seed `33033`. A unidade de
atribuição é a sessão de captura, agrupada por `room_id + capture_session_id`.
Frames, rajadas ou fotos da mesma sala e sessão nunca atravessam conjuntos.

Na primeira demonstração, o baseline não usa o conjunto de treino. A partição é
mantida desde já para que a avaliação e um eventual fine-tuning usem o mesmo
protocolo sem reconstrução oportunista.

### 5.2 Teste bloqueado

Threshold de confiança, NMS, classes e qualquer regra de pós-processamento são
escolhidos exclusivamente no conjunto de validação. Depois de congelar a
configuração, cada versão do modelo executa o teste uma única vez. Mudança após
ver o teste cria nova versão e deve ser declarada.

### 5.3 Cobertura mínima preliminar

- pelo menos 30 sessões independentes de captura;
- pelo menos 30 instâncias de teste por classe habilitada;
- iluminação adequada (≥ 300 lux), baixa (< 100 lux) e mista/contraluz;
- oclusão < 20%, entre 20% e 50% e > 50%;
- câmera parada e caminhada lenta;
- faixas relativas perto, média e distante;
- objeto único, múltiplos da mesma classe e cena desorganizada.

Contagens menores podem servir para smoke test, mas não podem alimentar as
métricas finais sem registrar a limitação.

## 6. Medição

### 6.1 Detecção

Serão reportados por classe e macro: precision, recall, AP@0,50 e AP@[0,50:0,95].
O relatório inclui verdadeiros/falsos positivos, falsos negativos e matriz de
confusão. Threshold é registrado junto do resultado.

### 6.2 Operação assistiva

- alertas falsos por minuto;
- taxa de eventos relevantes sem alerta;
- latência de inferência p50/p95;
- latência frame recebido → evento enfileirado p50/p95;
- tempo até o início do TTS, medido separadamente;
- FPS recebido/processado e frames descartados;
- memória, temperatura e bateria em ensaio sustentado de 20 minutos;
- falha, ANR ou crescimento contínuo de fila/memória.

As durações usam relógio monotônico. A medição de inferência descarta 30
execuções de aquecimento e usa ao menos 300 amostras válidas por configuração.

## 7. Aparelho de referência

A equipe selecionou o **Xiaomi POCO X5 Pro 5G** como aparelho físico de
referência. A especificação oficial registra chipset Qualcomm Snapdragon 778G e
variantes de 6 GB ou 8 GB de RAM. Esses valores descrevem a linha do produto;
não substituem o inventário da unidade usada no ensaio.

Imediatamente antes do benchmark, a equipe deve capturar no JSON, via aparelho
ou ADB:

- versão do Android efetivamente instalada;
- RAM da unidade física;
- hash SHA-256 do build fingerprint, sem publicar o identificador bruto;
- versão do aplicativo e commit;
- estado térmico e nível inicial de bateria.

A câmera já está configurada no mobile para câmera traseira, resolução média,
NV21 e alvo de 12 FPS. Emulador pode validar fluxo e erros, mas seus números não
são aceitos como desempenho do MVP.

## 8. Decisão após o baseline

1. **Passou:** integrar o artefato em REN-29 e manter as quatro classes.
2. **Falhou apenas `table_desk`:** coletar carteiras/mesas e avaliar fine-tuning.
3. **`door` tornou-se obrigatória:** coletar e anotar porta, treinar novo
   artefato e repetir todo o teste bloqueado.
4. **Latência falhou:** medir pré/pós-processamento, threads e delegates antes de
   trocar o modelo.
5. **Precision/recall falharam de forma ampla:** comparar modelo alternativo e
   registrar a decisão, sem escolher pelo conjunto de teste.

## 9. Aprovação e prontidão de execução

Em 19 de agosto de 2026, Renato Cesar aprovou classes, gates, política de dados
e o POCO X5 Pro 5G como aparelho de referência. O protocolo está `approved` e
`python -m eyes_project_ai.protocol` deve continuar passando.

A aprovação congela as decisões experimentais, mas não autoriza antecipar um
benchmark. A execução permanece `blocked` até que a REN-36:

- registre o SHA-256 e aprove a licença do artefato exato;
- capture Android, RAM, hash do build fingerprint, versão do app, commit,
  bateria e estado térmico da unidade física;
- remova os bloqueios de `execution_readiness` e altere seu status para `ready`.

Essa separação evita dependência circular: REN-33 aprova o protocolo que a
REN-36 usará para adquirir e verificar o artefato executável.

## 10. Fontes primárias

- [TensorFlow Lite: detecção de objetos no Android](https://www.tensorflow.org/lite/android/tutorials/object_detection)
- [TensorFlow: EfficientDet-Lite para mobile](https://blog.tensorflow.org/2021/06/easier-object-detection-on-mobile-with-tf-lite.html)
- [Mapa de classes COCO](https://docs.ultralytics.com/datasets/detect/coco/)
- [Licenciamento Ultralytics](https://www.ultralytics.com/license)
- [LGPD consolidada — Lei 13.709/2018](https://www.gov.br/mme/pt-br/arquivos/legislacao-consolidada-lgpd.pdf)
- [POCO X5 Pro 5G — página oficial do produto](https://www.mi.com/br/product/poco-x5-pro-5g/)
