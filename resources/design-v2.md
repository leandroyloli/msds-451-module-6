# Desenho v2: bloco C com compras, vendas e concentração por dentro dos ETFs

Pesquisa e revisão: 1 de novembro de 2026. Este memo propõe políticas para o
estudo; não fixa a tolerância pessoal do investidor nem comprova percentuais
universalmente ótimos. A implementação deve registrar os valores usados antes
de examinar a classificação dos resultados.

## 1. O que muda e o que permanece

O objetivo continua sendo escolher uma carteira de ETFs para o bloco C. Os
blocos de segurança e inflação ficam fora das variáveis de decisão, das
garantias e do financiamento. Os filtros de 60 retornos mensais completos,
mediana diária negociada de USD 1 milhão e pelo menos 100 observações nos seis
meses anteriores foram aprovados pelo usuário e permanecem causais.

Permitir posições negativas aumenta o conjunto de alternativas. Não impõe
uma posição vendida mínima. Se os custos e os limites fizerem a solução ótima
ficar comprada, esse resultado é legítimo. Não introduzir previsões ou pesos
manualmente para fazer aparecer uma venda.

A comparação principal passa a ser entre versões comprada e comprada/vendida
com a mesma base de dados, exposições auditáveis, custos e regras. VT e 1/N
continuam referências. Falhar uma margem contra o benchmark não converte
automaticamente o benchmark em uma nova carteira do fundo.

## 2. Retornos esperados: não amarrar a resposta ao benchmark

O prior anterior beta × 4% tem pouca informação independente do mercado. Ele
não é uma previsão de alpha. A literatura de Jorion (1986) sustenta reduzir o
erro das médias estimadas, mas não prova o peso 50/50 de uma mistura escolhida.

Há duas implementações honestas:

1. **Shrinkage empírico de médias.** O apêndice dos autores DeMiguel, Garlappi e
   Uppal explicita uma versão Bayes–Stein: média do ativo é misturada à média
   da carteira global de mínima variância, e a intensidade depende da dispersão
   das médias, da covariância e do tamanho da amostra. O conteúdo apareceu
   integralmente no índice de busca NBER, mas o PDF direto retornou 404; não
   afirmar leitura completa desse arquivo.
2. **Mistura fixa declarada.** Misturar média histórica e prior de mercado em
   proporção fixada antes do teste; 50/50 seria política do estudo, com
   sensibilidades 25/75 e 75/25, e não uma estimativa ótima comprovada.

Se usar o estimador empírico com covariância Ledoit–Wolf em vez da matriz
amostral corrigida de Jorion, chamar de shrinkage de médias inspirado em
Bayes–Stein. Não alegar reprodução exata do artigo. Fazer tudo só com os 60
retornos anteriores. Reestimar dentro de cada cenário sintético também.

Uma fórmula operacional inspirada no apêndice é:

```
m = média mensal amostral; C = covariância mensal regularizada
q = C^-1 1 / (1' C^-1 1)
m0 = q' m
phi = (N+2) / ((N+2) + T (m-m0 1)' C^-1 (m-m0 1))
m_shrunk = (1-phi) m + phi m0 1
```

O peso q serve ao estimador; não é a carteira recomendada e pode conter
posições negativas. O objetivo final aplica as restrições da carteira.

## 3. Limites vinculados a choques explícitos

Os valores abaixo são propostas prudenciais, não resultados de otimização
sobre a mesma janela que será usada para avaliar o desempenho.

| Limite sugerido | Razão operacional / orçamento de choque |
|---|---|
| Peso por ETF entre −5% e +20% | Limita uma venda isolada e a dependência de um veículo. A capacidade de aluguel real ainda precisa ser verificada. |
| Exposição líquida 100% | Mantém o bloco C orientado a ações; não significa ausência de dívida ou de garantias. |
| Exposição bruta até 140% | Com líquido 100%, implica compras até 120% e vendas até 20%. Não é meta de usar toda a alavancagem. |
| Empresa/grupo até 5% bruto | Choque isolado de 50% equivale a até 2,5 pontos percentuais de NAV, antes de choques simultâneos e custos. |
| Setor até 35% bruto | Choque setorial isolado de 40% equivale a até 14 pontos de NAV. Sensibilidades 30% e 40% mostram o custo desse orçamento. |
| Maior país até 75% bruto; demais até 25% | Políticas para limitar dependência geográfica. Um choque isolado de 30% no maior país pode consumir 22,5 pontos de NAV. Ajustar se esse orçamento for incompatível com o mandato. |
| CVaR 95% mensal até 15% | Limita a média dos piores 5% dos retornos mensais modelados. Não limita drawdown acumulado nem perda máxima fora dos cenários. |

Não somar restrições decorativas. O teto por família de ETF pode ser removido
quando empresa/setor/país completos já controlarem a exposição econômica;
mantê-lo apenas como controle operacional documentado. O mínimo obrigatório
de 20% de fundos globais não é necessário à nova lógica: a composição real
deve decidir se já há diversificação, sem impor um ticker ou wrapper.

**Moeda precisa de uma definição auditável.** Moeda de negociação do ETF não
é a moeda das empresas. A moeda de negociação de cada ação subjacente é uma
proxy, não uma medida de receitas, dívida ou hedge cambial econômico. Se
existir apenas essa proxy, identificar como tal. Não chamar de limite de
risco cambial econômico certificado. Um teto ilustrativo USD 85% bruto,
restantes 35%, pode ser testado somente se os dados completos dessa proxy
estiverem disponíveis e houver viabilidade; não é um resultado da literatura.

## 4. Look-through e dados incompletos

Para participações não negativas h[j,i] da empresa j no ETF i:

```
exposição líquida da empresa j = sum_i w_i h[j,i]
exposição bruta da empresa j   = sum_i abs(w_i) h[j,i]
```

As restrições devem usar a exposição bruta e o diagnóstico deve mostrar as
duas. Fazer o mesmo para setores e países. Assim uma compra e uma venda de
fundos quase iguais não escondem posições grandes.

Unir classes do mesmo emissor (por exemplo GOOG/GOOGL) com identificador
auditável. ADR e ação local podem ser a mesma empresa. Não afirmar que todo
grupo econômico foi consolidado se apenas as classes de ações foram unidas.
A metodologia GICS atribui classificação à empresa e a propaga aos títulos;
é necessário harmonizar classificações diferentes dos provedores. Não
chamar todos os rótulos setoriais de GICS se não houver mapeamento verificado.

Top 10 não é composição completa. Conservar uma parcela desconhecida, medir
cobertura e excluir fundos sem suporte suficiente para o controle prometido.
Não preencher desconhecido com zero nem normalizar artificialmente o Top 10
a 100%. Uma possibilidade conservadora é limitar a parcela desconhecida
agregada; para certificação forte de empresa, a parte desconhecida também
precisa entrar no pior caso de concentração de cada emissor.

**História:** uma composição de outubro de 2026 não estava disponível em
2019. Se só houver composição atual, ela pode definir uma carteira atual e
um teste retrospectivo com matriz congelada, mas esse teste não é uma
validação point-in-time dos limites por empresa/setor. O relatório deve
distinguir isso na própria tabela principal, não apenas numa nota distante.

## 5. Contabilidade de posições negativas e financiamento

Defina L como a soma dos valores comprados e S como o valor absoluto das
vendas, em proporção do NAV. A exposição líquida escolhida é L−S=1.
Uma carteira 120/20 tem risco bruto de 140%, não de 100%.

**Modelo explícito conservador de caixa restrito:** os recursos da venda
ficam em garantia e não são dinheiro gratuito para novas compras. Seja
K=hS o colateral, h>=1. Incluindo os recursos da venda na contabilidade:

```
dívida D = max(L - 1 - S + K, 0)
NAV = L + K - S - D
se L-S=1, então D=K e NAV=1
fluxo de financiamento = K*taxa_rebate - D*taxa_debito - S*taxa_aluguel
```

Para h=1 e rebate=0, hipótese conservadora de estudo, custo anual sobre a
venda é S*(taxa_caixa + spread_debito + taxa_aluguel). Isso não é uma
reprodução da conta de uma corretora específica. IBKR documenta que aluguel
e remuneração dos recursos da venda são componentes distintos, variáveis
com o papel e o tamanho da conta; alguns clientes não recebem o rebate cheio.

Sugestão inicial claramente assumida: spread de débito 1,5% a.a. e aluguel
2% a.a.; sensibilidades de aluguel 1%, 3% e 5%, sem escolher o caso vencedor.
Taxas históricas de aluguel e disponibilidade não foram observadas: sua
ausência limita qualquer alegação de executabilidade. Permitir vendas
somente de ETFs líquidos explicitamente marcados como candidatos a aluguel;
essa marca não equivale a um locate real.

**Distribuições:** se o retorno usado é o total ajustado, w negativo já
incorpora a obrigação econômica de distribuições. Não descontar dividendos
novamente. TER também já está no preço observado. Aluguel, financiamento,
gestão extra e transação continuam separados.

**Margem:** Regulação T/FINRA e house margins variam por produto e conta. Um
teste acadêmico pode usar requisito inicial simplificado 50% L + 50% S e
manutenção 25% L + 30% S, mas precisa rotular isso como proxy de títulos
ordinários, não compliance universal. Verificar que NAV satisfaz os requisitos;
após movimentos adversos, reduzir exposição ou registrar chamada/encerramento
forçado. Não recorrer aos blocos A/B. Testar recall/cobertura compulsória como
sensibilidade se não houver história de disponibilidade de aluguel.

## 6. Otimização e execução

O objetivo Sharpe líquido tem retornos esperados, custos e risco na mesma
unidade temporal. Na formulação por p e n não negativos, w=p−n; o total
vendido é sum(n) e o bruto é sum(p+n). Custos tornam inúteis posições
comprada e vendida simultâneas no mesmo ETF; verificar que o resultado não
contém essa redundância.

Para um alvo positivo de Sharpe, a desigualdade numerador >= alvo*sigma é
convexa quando o numerador é linear menos custos convexos; dá para resolver
por bisseção e programação cônica. Se usar SLSQP com valor absoluto e CVaR
amostral, verificar solução e tolerância e não prometer ótimo global.

CVaR por cenários mensais pode ser implementado com variável z e excessos u:

```
u_s >= perda_s(w)-z; u_s >= 0
z + sum_s u_s / ((1-alpha)*M) <= limite_CVaR
```

Isso é a média da cauda modelada. Com 60 observações e alpha=95%, a cauda é
muito pequena; declarar essa fragilidade. Bootstrap conjunto pode ampliar
os cenários mas não cria novos regimes. Choque universal de −50% nas ações
não pode ser conciliado com uma promessa de perda máxima 15% e exposição
líquida acionária próxima de um sem um hedge/ativo diferente. Tratar esse
choque separado de um CVaR mensal, sem relaxar a matemática silenciosamente.

Mensalmente, usar só dados até o sinal e executar depois; garantir que
as posições anteriores recebem o retorno até o fechamento da execução.
Vender para reduzir posição comprada e vender a descoberto são operações
distintas, mas ambas pagam custo de transação. Custos devem reduzir o NAV
em contabilidade autofinanciada. Peso negativo que cresce por movimento do
preço exige controle de margem e exposição também entre rebalanceamentos.

## 7. Comparação e relatório curto

Não adicionar uma exigência mínima de short e não concluir que usar todos os
61 fundos é melhor. Os 61 são candidatos e cada exclusão fica documentada.
Comparar mesma regra de retorno/covariância/caps com e sem posições negativas.
Manter pesos iguais e um ETF global como referências, sem convertê-los
automaticamente na carteira escolhida.

O HTML pt-BR pode concentrar-se em cinco perguntas: por que o fundo existe;
qual pesquisa fundamenta as decisões; como calcula pesos; o que testes e
custos mostraram; qual carteira de estudo resulta e o que falta validar.
Mostrar carteira, exposição por empresa/setor e restrições ativas antes de
longas descrições de implementação. Reservar fontes, 61 candidatos e contas
detalhadas para anexos recolhidos. Não alegar que 100% VT seja a nova
estratégia aprovada pelo usuário.

## Fontes primárias abertas nesta rodada

- Jorion (1986), resumo no editor Cambridge: erro de estimação de médias e
  justificativa de shrinkage de médias; texto integral não lido.
- DeMiguel/Garlappi/Uppal, apêndice NBER indexado: fórmula operacional de
  Bayes–Stein. Abertura direta 404, acesso limitado explicitado.
- Rockafellar/Uryasev, página de publicações do autor e resumo original no
  editor (2002): CVaR em distribuições por cenários e distinção de drawdown.
- MSCI GICS, PDF atual servido como abril de 2026 embora o URL contenha
  20250220: classificação no nível da empresa e propagação aos títulos.
- FINRA Rule 4210: definição de patrimônio e manutenção de margem.
- IBKR Short Sale Cost, página de financiamento e requisitos: distinção de
  aluguel/rebate, variabilidade de taxas e dependência do tipo de conta.
