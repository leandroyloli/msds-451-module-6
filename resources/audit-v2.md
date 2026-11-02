# Revisão independente da implementação v2

Revisão retomada após reinício do servidor. Escopo: `model_v2.py`,
`study_v2.py`, `execution_v2.py` e `simulation_v2.py`. Não é certificação de
desempenho nem de uma carteira real. Os resultados finais ainda dependem da
execução e dos dados de composição congelados pelo responsável pelo estudo.

## Achados materiais e correções verificadas no código

1. A projeção por bandas originalmente consultava os pesos depois do retorno
   do fechamento que também executava a ordem. Agora usa `old_signal`, o mesmo
   retrato anterior empregado pela otimização. Achado resolvido.
2. Resíduos numéricos da igualdade dos pesos podiam violar a identidade de
   caixa mais estrita. Os produtores de pesos normalizam o resíduo e voltam a
   verificar limites e CVaR. Achado resolvido.
3. A banda originalmente não repetia todos os testes depois da normalização.
   A versão inspecionada verifica soma, posições, exposição bruta, A|w| e CVaR.
   Achado resolvido.
4. Uma insolvência não pode continuar a operar e recuperar espontaneamente.
   O histórico agora liquida, conserva o déficit e congela a estratégia;
   métricas convencionais ficam indefinidas quando houver insolvência.
   Não se trunca uma perda superior a 100% para aparentar proteção.

## Matemática e contabilidade

- A transformação homogênea do Sharpe é coerente quando o excesso esperado
  positivo existe. A revisão anterior desta mesma tarefa comparou o resultado
  com SLSQP independente em dez ativos sintéticos: diferença do Sharpe de
  aproximadamente 6,2e-11, sem violação. Esse teste é registrado como evidência
  da revisão anterior, não como execução repetida após o reinício.
- As variáveis compradas e vendidas impõem A(p+q); a verificação final usa
  A|w|. Isso limita concentração bruta e não deixa compensações líquidas
  esconderem grandes posições.
- O estimador de médias é inspirado em Bayes–Stein, com adaptação da
  covariância para Ledoit–Wolf; não é reprodução exata de Jorion nem prior VT.
- `Account` distingue posições, caixa, garantia e financiamento. Proceeds não
  entram duas vezes no patrimônio. Retornos ajustados já incorporam o efeito
  das distribuições, inclusive para posições negativas.
- Custos correntes passam por caixa/dívida, sem vendas invisíveis diárias.
- As 23 verificações sintéticas de `execution_v2.self_test()` foram repetidas
  após a retomada, sem gravar sobre resultados reais.

## Condições para interpretação e entrega

- **Sem certificação histórica de composição:** arquivos atuais de setembro/
  outubro de 2026, aplicados a 2019, são um experimento retrospectivo de matriz
  congelada. A cronologia dos preços não resolve esse viés de composição.
- Se todo excesso esperado for negativo, o código emprega mínima variância
  com o mesmo mandato. Contar e relatar essas decisões; não chamar todos os
  períodos de maximização de Sharpe.
- `TC × 12 × turnover` é a anualização do custo projetado do mês da decisão,
  não uma previsão independente do giro anual.
- As métricas em `diag` de `trades.csv` são calculadas antes da projeção por
  bandas. Recalcular se forem apresentadas como previsão da carteira executada,
  ou identificá-las como diagnóstico do alvo otimizado.
- Cobertura de emissores, classificação setorial, conversões e fonte dos
  dados faltantes precisam de auditoria final dos arquivos estabilizados.
- Moeda de negociação dos títulos é uma proxy observável, não exposição
  econômica às receitas e dívidas das empresas.
- Aluguel, financiamento, disponibilidade e margem são hipóteses do estudo,
  não condições históricas verificadas de todos os ETFs e corretores.

Conclusão: não foi identificado novo bloqueio matemático nas versões
inspecionadas. Isso não substitui testes dos resultados reais e do HTML final.
