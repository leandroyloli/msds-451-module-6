# Contabilidade da carteira comprada e vendida — v2

O arquivo `pipeline/execution_v2.py` acrescenta uma conta assinada ao estudo.
Ele não altera preços, resultados ou código da versão anterior. As restrições
de alocação pertencem ao modelo chamador; esta classe cuida do dinheiro.

## API

- `Account(initial_nav=1)` começa com uma unidade de caixa e nenhuma posição.
- `holdings` contém valores em USD: positivos comprados e negativos vendidos.
- `cash`, `collateral` e `debt` são saldos distintos em USD.
- `nav` é `sum(holdings) + cash + collateral - debt`.
- `long_value` e `short_value` são valores absolutos em USD.
- `long`, `short`, `gross` e `net` são exposições divididas pelo NAV.
- `margin_required` é o valor em USD da política de manutenção;
  `margin_ratio` é esse valor dividido pelo NAV.
- `rebalance(target, cost_rate=.001)` executa pesos cuja soma líquida é um.
- `mark(returns)` aplica os retornos totais de um período e remarca garantias.
- `accrue(days, rfannual, ...)` lança juros e taxas pelo caixa/débito.
- `liquidate(cost_rate=.001)` encerra as posições, libera garantias e quita o
  débito até onde o patrimônio permite. Um saldo devedor remanescente fica
  registrado; não se transforma insolvência em uma conta de caixa positiva.

## Uma venda não cria patrimônio

Para pesos líquidos somando 100%, uma carteira com 120% comprado e 20% vendido
continua com patrimônio de 100%. Sua exposição bruta é 140%.

Adotamos como hipótese conservadora de estudo que o produto da venda fica
integralmente restrito em garantia, sem remuneração. Com vendido `S` e
multiplicador de garantia `h`, a garantia é `h*S`. O financiamento separado
necessário para sustentar a carteira líquida é também `h*S` após o rebalanceamento.

No caso `h=1`, os valores são:

| Saldo | Valor por unidade de patrimônio |
|---|---:|
| ETFs comprados | 1,20 |
| ETFs vendidos, obrigação | −0,20 |
| Caixa restrito em garantia | +0,20 |
| Financiamento | −0,20 |
| Patrimônio líquido | 1,00 |

Assim não contamos o produto da venda duas vezes. Se a posição vendida sobe,
a garantia exigida cresce e o débito financia essa transferência. Se cai, a
liberação de garantia primeiro reduz o débito. Transferir garantia não gera
lucro ou perda; apenas a variação do ativo e os encargos mudam o NAV.

## Custos

As hipóteses padrão, alteráveis explicitamente pelo chamador, são:

- Gestão adicional: 0,25% ao ano sobre o patrimônio positivo.
- Aluguel: 2% ao ano sobre o valor vendido.
- Financiamento: taxa anual USD defasada fornecida pelo chamador mais 1 ponto
  percentual, sobre o débito efetivamente registrado.
- Remuneração da garantia: zero no cenário padrão.
- Caixa livre: remuneração pela taxa USD fornecida, salvo configuração diferente.
- Negociação: 0,10% sobre todo valor comprado ou vendido, inclusive abrir e
  fechar posições negativas e a entrada inicial.

Os encargos usam dias corridos/365 e são pagos pelo caixa ou pelo financiamento.
**Não vendemos ou redimensionamos posições silenciosamente todo dia para pagar
taxas.** O débito acumulado reduz o NAV e só é liquidado economicamente na próxima
negociação ou no encerramento.

Retornos ajustados já incorporam distribuições no resultado dos ativos. Uma
posição negativa multiplicada pelo retorno total tem o sinal oposto, incluindo
essas distribuições. Cobrar novamente dividendos do vendido duplicaria o custo.
Esta é uma representação por unidades de retorno total, não um livro de ações,
proventos e datas de pagamento individualizadas.

## Rebalanceamento autofinanciado

Com valores assinados anteriores `v`, pesos-alvo `w`, custo proporcional `c` e
patrimônio anterior `N`, resolvemos:

`N_depois = N - c * sum(abs(w * N_depois - v))`.

Depois abrimos os valores `w * N_depois`. Garantia e débito novos se compensam;
os custos de juros já acumulados não são perdoados. A conservação do caixa é
verificada também pela identidade independente entre compras, vendas e a
liquidação do financiamento anterior.

## Garantias, chamadas e falhas

A política de manutenção usada pela classe é `0,25*comprado + 0,30*vendido`, em
USD. Ela é uma hipótese do experimento e **não certifica** margens de uma
corretora, mercado ou ETF. Disponibilidade de aluguel, mudanças de taxa,
recolhimento do empréstimo e diferenças entre instrumentos ainda exigem dados
de operação. O material primário de custos e margem é tratado no memo de
desenho; esta implementação não inventa termos individuais de corretagem.

`margin_breached` sinaliza a insuficiência; a classe não decide uma venda na
mesma cotação que acabou de revelar a chamada. O motor temporal deve agendar
a ação em um instante executável posterior. Insolvência é retida como evento,
sem excluir uma trajetória ruim do Monte Carlo.

## Verificação

`self_test()` retorna verificações sem gravar arquivo por padrão. A gravação
é explícita, por exemplo:

```powershell
uv run --no-project --with-requirements requirements.txt python -m pipeline.execution_v2 --self-test --output output/execution_v2_checks.json
```

Os exemplos verificam entrada, perdas e ganhos de uma posição negativa,
garantias sem lucro fictício, custos, ausência de negociação diária oculta,
encerramento solvente e insolvente e cem períodos de movimentos aleatórios.
