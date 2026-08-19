# ADR 0001: baseline pré-treinado EfficientDet-Lite0

- **Status:** proposto
- **Data:** 2026-08-19
- **Linear:** REN-33

## Contexto

O MVP precisa provar câmera → detecção → proximidade → feedback no Android antes
de investir em dataset e treinamento. A documentação citava YOLOv8n, mas não
existiam pesos, configuração, métricas, decisão de licença ou aparelho de
referência. As quatro classes iniciais `person`, `chair`, `backpack` e
`dining table` já existem no COCO; `door` não existe.

Ultralytics informa que código e modelos YOLO são oferecidos sob AGPL-3.0 ou
licença comercial. O projeto ainda não aprovou a aplicação de AGPL a toda a
solução nem uma licença comercial. O baseline também precisa chegar ao Flutter
como TensorFlow Lite com o menor número possível de conversões.

## Decisão

1. Usar EfficientDet-Lite0 pré-treinado em COCO como baseline da demonstração.
2. Executar localmente via TensorFlow Lite, com entrada 320 × 320 RGB.
3. Habilitar `person`, `chair`, `table_desk` por mapeamento para `dining table`
   e `backpack`.
4. Manter `door` na taxonomia, porém desabilitada até existir modelo customizado.
5. Não treinar na primeira demonstração; usar REN-34/35 somente se os gates do
   protocolo falharem ou porta for confirmada como obrigatória.
6. Exigir URL, SHA-256, metadados e revisão de licença antes de distribuir o
   artefato no app.
7. Manter YOLO como comparador opcional, condicionado a ADR de licença próprio.

## Consequências

### Positivas

- primeiro incremento menor e diretamente compatível com runtime mobile;
- nenhuma métrica falsa ou custo de treinamento para mostrar a integração;
- classes suportadas e não suportadas ficam explícitas;
- fine-tuning passa a responder a evidência, não a preferência de ferramenta;
- risco de licença é tratado antes de embutir pesos no aplicativo.

### Negativas

- porta não estará disponível na primeira demonstração;
- carteiras escolares podem sofrer domain shift em relação a `dining table`;
- o modelo pode ter menor precisão que alternativas mais recentes;
- ainda será necessário escolher e registrar um aparelho físico.

## Alternativas consideradas

### YOLOv8n pré-treinado

Vantagem de ecossistema e histórico no texto do TCC. Rejeitado como baseline
obrigatório porque adiciona conversão e uma decisão AGPL/comercial ainda não
aprovada. Continua candidato de experimento.

### Treinar modelo customizado imediatamente

Rejeitado: aumentaria coleta, anotação e risco científico antes de medir o que o
modelo pré-treinado já entrega.

### ML remoto

Rejeitado no MVP por latência, dependência de rede e exposição de imagens.
