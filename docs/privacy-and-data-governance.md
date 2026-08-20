# Privacidade e governança de dados de visão

## 1. Escopo

Esta política rege imagens e anotações produzidas para avaliação ou futuro
treinamento. Ela não substitui análise jurídica, ética ou institucional. O
princípio do MVP é **processar no aparelho e não persistir pixels**.

## 2. Aplicativo

- frames existem apenas em memória durante câmera → inferência;
- o aplicativo não salva foto, vídeo, crop ou embedding;
- pixels não são enviados ao backend, analytics ou serviço de nuvem;
- logs contêm apenas versão, duração, contadores e códigos técnicos;
- não há reconhecimento facial, biometria ou inferência de identidade;
- sincronização futura, se aprovada, limita-se a metadados agregados e consentidos.

## 3. Coleta experimental gravada

A coleta ocorre somente em atividade separada do uso normal do app e exige:

1. finalidade, classes, local, prazo e responsáveis documentados;
2. consentimento explícito antes da gravação;
3. opção real de recusa e revogação sem prejuízo;
4. voluntários adultos no conjunto inicial da classe `person`;
5. sala preparada para não capturar terceiros;
6. transferência imediata para armazenamento controlado e criptografado;
7. acesso nominal mínimo e registro de quem exportou os dados;
8. proibição de nuvem pessoal, mensageria e repositório Git.

Se uma pessoa não consentida aparecer, o material é descartado. Blur posterior
não transforma coleta indevida em coleta autorizada.

## 4. Crianças e adolescentes

O dataset inicial não inclui menores. Qualquer mudança exige, antes da captura:

- avaliação da instituição de ensino e do processo ético aplicável;
- demonstração do melhor interesse da criança ou adolescente;
- base legal documentada;
- consentimento específico e destacado do responsável quando aplicável;
- informação simples e acessível ao participante;
- minimização, direito de revogação e processo verificável de exclusão.

Essa cautela reflete o art. 14 da LGPD e não é autorização jurídica automática.

## 5. Retenção e descarte

| Artefato | Prazo inicial | Destino |
|---|---:|---|
| Captura bruta | até 30 dias após revisão | exclusão segura |
| Cópia rejeitada/sem consentimento | imediata | exclusão segura |
| Anotação derivada | condicionada a licença e consentimento | dataset versionado ou exclusão |
| Termo de consentimento | conforme regra institucional | repositório administrativo separado |
| Métrica agregada | duração do TCC | documento de resultados sem identificação |

O identificador que liga consentimento a sessão fica separado do dataset. A
exclusão é registrada por ID pseudônimo e não exige conservar a imagem.

## 6. Licença e proveniência

Para cada fonte pública ou própria, o manifesto registra:

- URL/origem e responsável pela aquisição;
- licença vigente e data de acesso;
- uso permitido, atribuição e restrições;
- hash do arquivo ou snapshot;
- transformações e revisões;
- decisão de aceitar ou rejeitar a fonte.

“Disponível na internet” não é licença. Um modelo ou imagem sem termos
verificáveis não pode ser redistribuído no aplicativo nem no dataset.

## 7. Incidente

Em caso de acesso indevido, perda ou publicação acidental:

1. interromper coleta e compartilhamento;
2. preservar apenas evidência técnica não imagética necessária;
3. notificar responsável do projeto e instituição;
4. identificar sessões afetadas pelo ID pseudônimo;
5. revogar acessos, excluir cópias não autorizadas e documentar a resposta;
6. avaliar obrigações de comunicação com apoio institucional competente.

## 8. Checklist antes da captura

- [ ] responsável e finalidade aprovados;
- [ ] ambiente sem terceiros não consentidos;
- [ ] participante adulto e termo válido no conjunto inicial;
- [ ] armazenamento criptografado e prazo configurado;
- [ ] IDs pseudônimos preparados;
- [ ] plano de descarte testado;
- [ ] fontes e licenças registradas;
- [ ] nenhuma sincronização automática de fotos habilitada.
