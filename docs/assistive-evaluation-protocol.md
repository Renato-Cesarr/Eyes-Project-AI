# Protocolo unificado de avaliação assistiva — REN-68

## Autoridade, versão e escopo
Contrato normativo: [assistive-evaluation.v1.json](../config/assistive-evaluation.v1.json), ID `eyes-assistive-evaluation-v1`, revisão 05/10/2026. O repositório IA é a fonte; o mobile mantém uma cópia normalizada LF, com o mesmo SHA-256. `experiment.v1.json` referencia esse digest e o validador rejeita divergências. Não manter duas decisões científicas independentes.

Este documento consolida o protocolo IA e REN-37 antes da coleta final. Não altera EfficientDet-Lite0, políticas de proximidade, câmera, inferência, TTS, háptico ou privacidade. Pessoa/cadeira/mesa/mochila continuam habilitadas; `table_desk` na IA corresponde a `table` no mobile, hipótese de transferência de `dining table`. Porta permanece fora do baseline. Distâncias 0,50/1,00/2,00 m são referências de montagem, sem atribuir medição métrica ao produto.

## Marcos de latência, n e aquecimento

| Métrica | Marco e unidade | Meta preservada | Amostra / evidência |
| --- | --- | --- | --- |
| Inferência | duração do interpretador, ms, relógio monotônico/Stopwatch | p95 ≤250 ms | ≥300 inferências válidas por configuração, após 30 frames e 5 s de aquecimento |
| Frame → decisão | `captured_at → observed_at`, ms | Sem gate adicional inventado | n de frames com duração válida; não trocar por inferência |
| Frame → fila | `alert.source_at → alert.emitted_at`, ms | p95 ≤500 ms (IA) | n de alertas; frame original do evento, não abertura da sessão |
| Fila → TTS | `alert.emitted_at → speech.started_at`, ms | Diagnóstico separado | n de pares por sessão e correlation_id |
| Frame → TTS | `alert.source_at → speech.started_at`, ms | p95 ≤300 ms (REN-37) | n de pares válidos, separado dos frames |
| Primeiro alerta operacional | primeiro frame medido → primeiro alerta da sessão/janela | Sem gate adicional inventado | Uma amostra por sessão com frame/origem disponível |
| Abertura → primeiro alerta | `session_started → primeiro alert.emitted_at` | Diagnóstico de preparação | Separado do tempo operacional; não rotular como inferência |

Não comparar ≤500 ms até fila com ≤300 ms até fala como se fossem a mesma medição. Preservar os três gates; um pode passar enquanto outro falha. O relatório sempre informa p50/p95, n, ms, método, versão/configuração e condições. Percentil usa interpolação linear com rank=(n−1)×p/100. Ausência de pares/marcos permanece indisponível; não converter latência negativa em zero.

**Plano TTS proposto:** reunir 100 pares válidos por configuração em sessões independentes. É uma decisão de planejamento de engenharia adicionada nesta revisão, sem mudar o limite de 300 ms: em n=100 a cauda superior de 5% contém aproximadamente cinco observações. Isso não é intervalo de confiança nem prova de segurança. Congelar/revisar esse plano antes da coleta final; não extrapolar quatro pares do piloto. O mínimo histórico de 300 amostras do protocolo IA se aplica à inferência, não automaticamente ao TTS.

**Limite do relógio atual:** durações internas usam Stopwatch; deltas entre `captured_at`, fila e TTS usam UTC/DateTime. A análise rejeita reversões detectáveis, mas isso não demonstra relógio monotônico ponta a ponta nem precisão de sincronização nativa/Dart. Verificar instrumentação dos marcos/relógios na REN-37 antes de usar o gate final como resultado físico conclusivo. O tempo de fala é início nativo, não retorno de `speak`.

## Denominadores e condições
- Precision/recall/mAP exigem caixas e eventos anotados, por classe e macro. Preservados: precision/recall ≥0,60; mAP@0,50 ≥0,50; IoU≥0,50 conforme o protocolo IA.
- Perigo perdido **por frame**: frames esperados attention/veryNear preditos distant/missed ÷ todos os frames esperados de perigo. Descrever esse diagnóstico pelo seu denominador; não é taxa de incidentes nem recall global.
- Falso alerta **por frame distante**: frames distant com anúncio ÷ frames distant. Não é alertas falsos por minuto.
- Gate de falsos alertas: eventos de alerta anotados como falsos ÷ minutos medidos, ≤1/min. Gate de eventos relevantes sem alerta: eventos anotados perdidos ÷ eventos relevantes anotados, ≤0,40.
- Repetição: mesma sessão/classe/faixa/direção com intervalo inferior ao cooldown de 6 s; publicar contagem e contexto.
- Publicar também grupos por classe, faixa, luz e oclusão. Um agregado favorável não substitui resultados de condições que falham. Frames sequenciais são correlacionados; informar sessões independentes além do número de frames.

## Desenho dos conjuntos e congelamento
Corpus de detecção: mínimo de 30 sessões independentes e 30 instâncias de teste por classe habilitada; split 70/15/15, seed 33033, por sala+sessão. A documentação e os rótulos de classes/luz/oclusão permanecem normativos. Não dividir frames de uma mesma captura entre validação e teste.

Ensaio assistivo: 48 segmentos de calibração (4 classes ×3 faixas ×2 iluminações ×2 oclusões), 24 segmentos novos de avaliação balanceados e ≥6 negativos distant. Cada segmento tem 20 s medidos depois de ≥5 s e ≥30 frames de aquecimento; contraluz é cobertura adicional. Calibração e avaliação precisam de montagens/exemplares/ordens diferentes. Segmentos curtos não substituem o corpus anotado de detecção nem a janela de estabilidade.

Congelar APK/commit, modelo/política, threads, FPS, câmera, thresholds e finalidade antes de avaliar. Não escolher parâmetros pelo teste. Mudança após ver o teste exige nova versão e declaração. Guardar registro de sala/sessão/split pseudônimo e revisar reutilização entre conjuntos; o validador de relatório garante homogeneidade das entradas, mas não comprova sozinho a independência física de sessões fora do manifesto.

Finalidades distintas: fixture, pilot, calibration, evaluation, negative e stability. Negative/stability usam split evaluation, sem escolha de parâmetros. Nenhum fixture alimenta resultado final. Reportar resultados em artefato separado; valores medidos do contrato continuam nulos.

## Janela sustentada e bateria
Executar **20 minutos medidos**, após aquecimento, cobrindo a exigência maior da IA e substituindo a previsão mobile de 15 min. Registrar condições de aproximação/afastamento, memória PSS/RSS, temperatura/estado térmico, ANR/fatal, filas e eventos. Não converter 2.040 frames históricos em 20 min sem timestamps.

Consumo de bateria exige ausência de carregamento registrada no começo/fim e durante a sessão; nível percentual isolado não mede energia. Se conectado, relatar condição e classificar consumo como não validado. Fixar brilho/rede/modo de uso e registrar versão/aparelho. Análise de estabilidade/consumo é prova física própria; o gerador descritivo não certifica esses gates.

## Proveniência e gerador mobile
O mobile exige `--manifest` para ensaios com finalidade calibration/evaluation/negative/stability. O manifesto identifica protocolo/digest, finalidade/split, build congelado, runtime e, por fonte: arquivo, SHA-256, sessão/cenário, metadados físicos e SHA-256, início operacional e janela medida. Os metadados físicos devem vir da coleta e conter a identidade do APK; versões divergentes, fontes não declaradas, hashes/sessões incompatíveis, pares TTS duplicados/órfãos ou aquecimento insuficiente interrompem a geração antes de escrever.

Fluxo: copiar o exemplo mobile, preencher **somente evidências reais**, revisar/congelar; gerar um relatório por finalidade/configuração. Pastas são permitidas apenas com todas as fontes declaradas. `--legacy-purpose pilot|fixture` aceita um arquivo exato e deixa explícitos janela/aquecimento/build não verificados; não habilita uma migração fictícia para avaliação final. O resumo JSON contém recibos, n por métrica e grupos de condições.

Para o primeiro alerta, a origem passa a ser o primeiro frame medido; abertura da sessão fica em outra série. Sem timestamp do frame, o resultado operacional é indisponível. Nenhum script de análise inicia câmera ou coleta, muda consentimento ou habilita calibração em produção.

## Classificação das evidências históricas
REN-29 (21/08): benchmark físico de inferência/pipeline, 300 frames após 30 de aquecimento, médias e janela de 2.040 frames. Não fornece p95 de TTS, precisão em corpus final ou estabilidade de 20 min automaticamente.

Piloto REN-37 (16/09): 550 frames, cinco alertas, quatro pares TTS; um cenário chair/veryNear/bright/none. Perigo perdido 502/550 (91,27%) é indicador por frame. Frame→TTS p95 685,66 ms é diagnóstico de apenas quatro pares, acima da meta; sem generalização. A reanálise distingue abertura→primeiro alerta 52.204,63 ms de primeiro frame→primeiro alerta 10.919,07 ms (uma sessão, janela legada não verificada). A diferença de origem não prova melhoria de latência. Originais permanecem intactos; reanálise identificada fora do inventário original.

## Prontidão
[Inventário com proveniência](runtime-inventory-2026-10-05.md). Protocolo/tooling versionados não encerram coleta, calibração, corpus, avaliação ou aceite físico. Permanecem: inventário atual completo para o build medido, montagem independente, plano TTS revisado/congelado, instrumentação de relógios conferida, coleta/anotações, estabilidade e relatório com resultados negativos. REN-37/34/69/32/72 mantêm essas provas.


[Recibo versionado da reanálise do piloto](evidence/REN-68-legacy-pilot.json): fontes SHA-256, software dc5d0ed limpo, n por métrica e limitações; sem identificador bruto do aparelho. Companion de tooling: [MR Mobile #20](https://github.com/Renato-Cesarr/Eyes-Project-Mobile/pull/20).
