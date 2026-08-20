# Guia de anotação do MVP

## 1. Princípios

1. Anotar o objeto físico, não sua sombra, reflexo, foto ou representação em tela.
2. Usar a menor caixa retangular que contenha toda a porção visível do objeto.
3. Não estimar a parte invisível: a caixa cobre apenas pixels observáveis.
4. Uma instância física gera uma caixa, mesmo quando parcialmente ocluída.
5. Dúvida de classe não é resolvida por palpite; marcar para revisão ou excluir.
6. O annotator não usa a predição do modelo como verdade sem revisão humana.

## 2. Critérios gerais

### Inclusão

- objeto real e identificável pela parte visível;
- pelo menos 20% da área estimada do objeto está visível;
- maior lado visível possui pelo menos 16 pixels na imagem original;
- caixa pode ser definida sem englobar outra instância como se fosse uma só.

### Exclusão

- menos de 20% visível ou identidade de classe incerta;
- objeto apenas em fotografia, monitor, cartaz, espelho ou desenho;
- desfoque impede definir classe ou caixa;
- instância cortada sem características suficientes para revisão independente;
- classe fora da taxonomia fechada.

Exclusões são registradas por motivo, não simplesmente apagadas da auditoria de
qualidade.

## 3. Regras por classe

### `person`

- incluir adulto real, em pé ou sentado, sem inferir identidade;
- caixa cobre toda a porção corporal visível, incluindo membros observáveis;
- pessoas separadas recebem caixas separadas, ainda que se sobreponham;
- excluir fotos, reflexos, estátuas, manequins e pessoas em telas;
- o conjunto inicial usa somente voluntários adultos consentidos.

### `chair`

- uma caixa por cadeira individual, ocupada ou vazia;
- incluir cadeira parcialmente sob mesa se assento/encosto permitir identificação;
- excluir banco, sofá, arquibancada e desenho de cadeira;
- cadeiras empilhadas recebem caixas individuais apenas quando separáveis.

### `table_desk`

- incluir mesa, carteira escolar e superfície de apoio equivalente;
- uma caixa por unidade física; conjunto modular separável recebe caixas distintas;
- excluir prateleira, quadro, armário e apenas uma pilha de livros;
- registrar `domain_shift=dining_table_to_school_desk` na avaliação do baseline.

### `backpack`

- incluir mochila de costas com alças próprias, usada ou apoiada no chão/móvel;
- excluir bolsa, mala, sacola, estojo e capa de notebook;
- mochila parcialmente atrás de cadeira é incluída se ≥ 20% e identificável.

### `door`

- incluir folha física de porta aberta, fechada ou entreaberta;
- a caixa cobre a folha visível, não toda a parede ou apenas o batente;
- excluir vão sem folha visível, janela, portão e representação em imagem;
- anotações são permitidas para preparar futuro dataset, mas a classe não entra
  na avaliação do baseline COCO.

## 4. Oclusão, truncamento e multidão

- `occlusion=none`: menos de 20% encoberto;
- `occlusion=partial`: 20% a 50% encoberto;
- `occlusion=heavy`: mais de 50% encoberto, ainda respeitando 20% visível;
- `truncated=true` quando a imagem corta o limite físico do objeto;
- cenas com instâncias inseparáveis são marcadas para revisão, nunca fundidas em
  uma única caixa por conveniência.

## 5. Processo de qualidade

1. annotator primário rotula sem consultar o split final;
2. segundo revisor verifica 100% do teste e amostra mínima de 20% dos demais;
3. discordâncias de classe ou IoU entre caixas abaixo de 0,80 são conciliadas;
4. revisão registra decisão e responsável sem inserir nome de pessoa fotografada;
5. duplicatas e frames quase idênticos são removidos antes do split;
6. relatório final publica contagem por classe, cenário, split e exclusão.

## 6. Convenção de IDs

```text
room_<pseudonym>__session_<uuid>__frame_<monotonic-index>
```

Nome, matrícula, turma, escola, e-mail ou identificador de dispositivo não
entram no nome do arquivo ou na anotação.
