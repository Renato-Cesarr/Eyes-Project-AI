# Contrato do modelo EfficientDet-Lite0 do MVP

- **Linear:** REN-36
- **Manifesto normativo:** [`config/model-manifest.v1.json`](../config/model-manifest.v1.json)
- **Modelo:** EfficientDet-Lite0 pré-treinado em COCO 2017, inteiro quantizado
- **Formato:** TensorFlow Lite com metadados e pós-processamento embutidos
- **Licença declarada pelo publisher:** Apache-2.0
- **Revisão:** 20 de agosto de 2026

## 1. Proveniência e integridade

O artefato é o mesmo referenciado pelo exemplo oficial de detecção de objetos
do TensorFlow. O binário não é versionado neste repositório: ele é adquirido
por URL HTTPS fixa e só é publicado no destino local depois de conferir tamanho,
SHA-256, arquivo de labels e os quatro mapeamentos habilitados.

| Campo | Valor |
|---|---|
| Arquivo | `efficientdet-lite0.tflite` |
| Tamanho | `4.563.519` bytes |
| SHA-256 | `2e04c53bfeac0ac2a30c057c7e2a777594ce39baaac35a92f74fb1e8c4fc4e0b` |
| Labels embutidos | `labelmap.txt`, 90 linhas |
| SHA-256 dos labels | `f8803ef7900160c629d570848dfda4175e21667bf7b71f73f8ece4938c9f2bf2` |

Aquisição e inspeção:

```powershell
py -3.11 -m uv run python -m eyes_project_ai.acquire_model
py -3.11 -m uv run python -m eyes_project_ai.inspect_model
```

Arquivos diferentes, downloads incompletos e labels incompatíveis são rejeitados.
O arquivo temporário é removido e nunca substitui um artefato válido.

## 2. Contrato de entrada

| Propriedade | Valor |
|---|---|
| Nome | `serving_default_images:0` |
| Shape | `[1, 320, 320, 3]` |
| Tipo | `uint8` |
| Cor | RGB |
| Faixa | 0 a 255 |
| Resize | bilinear para 320 × 320 |

A orientação EXIF é aplicada antes da conversão RGB no runner Python. O Mobile
deve fazer rotação/espelhamento de câmera antes de montar o tensor e produzir o
mesmo layout NHWC. Não há normalização adicional para `[-1, 1]` ou `[0, 1]`.

## 3. Contrato de saída

O modelo já inclui decodificação e NMS. Aplicar outro NMS por padrão produziria
uma segunda política de supressão e quebraria a paridade com o baseline.

| Semântica | Tensor | Shape | Tipo |
|---|---|---|---|
| Caixas | `StatefulPartitionedCall:3` | `[1, 25, 4]` | `float32` |
| Classes | `StatefulPartitionedCall:2` | `[1, 25]` | `float32` |
| Scores | `StatefulPartitionedCall:1` | `[1, 25]` | `float32` |
| Contagem | `StatefulPartitionedCall:0` | `[1]` | `float32` |

As caixas usam `ymin, xmin, ymax, xmax` normalizados. O máximo é 25 detecções.
O threshold `0,40` é apenas candidato inicial e deve ser congelado no conjunto
de validação, conforme o protocolo experimental.

## 4. Mapeamento de classes

O label map do arquivo tem 90 posições e preserva lacunas dos IDs COCO. Isso é
diferente do índice contíguo de 80 classes usado por algumas bibliotecas.

| Domínio Eyes | Label | Índice de saída | ID oficial COCO | Índice COCO contíguo |
|---|---|---:|---:|---:|
| `person` | `person` | 0 | 1 | 0 |
| `chair` | `chair` | 61 | 62 | 56 |
| `table_desk` | `dining table` | 66 | 67 | 60 |
| `backpack` | `backpack` | 26 | 27 | 24 |

`door` continua desabilitada: o COCO não oferece essa classe. A aplicação deve
ignorar todas as classes não listadas, mesmo quando o score for alto.

## 5. Runner de referência

```powershell
py -3.11 -m uv run python -m eyes_project_ai.tflite_runner `
  caminho/para/imagem.jpg --warmup 30 --iterations 300 --threads 4
```

A saída JSON identifica o hash do modelo, as detecções filtradas e p50/p95 da
inferência. Esses números são de host e não substituem o benchmark no POCO X5
Pro 5G. O runner mede somente `invoke`; decode, resize, feedback e TTS exigem
medições separadas no Mobile.

## 6. Handoff para REN-29

1. adquirir os bytes e verificar tamanho/SHA antes de copiá-los para assets;
2. incluir a atribuição e a licença Apache-2.0 na distribuição mobile;
3. validar os nomes, shapes e tipos dos cinco tensores durante a inicialização;
4. usar quatro threads como candidato inicial, sem declarar desempenho antes do ensaio;
5. filtrar pelos índices deste contrato e pelo threshold versionado;
6. descartar frames sob backpressure, sem criar fila de inferências;
7. manter imagens exclusivamente no aparelho e não persistir frames por padrão;
8. tratar falha de carga/contrato como estado acessível e seguro, nunca como silêncio.

## 7. Fontes primárias

- [Model card oficial do TensorFlow](https://www.kaggle.com/models/tensorflow/efficientdet/tfLite/lite0-detection-default)
- [Script de aquisição do TensorFlow Examples](https://github.com/tensorflow/examples/blob/master/lite/examples/object_detection/raspberry_pi/setup.sh)
- [Tutorial oficial TensorFlow Lite para Android](https://www.tensorflow.org/lite/android/tutorials/object_detection)
- [Licença Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0)
