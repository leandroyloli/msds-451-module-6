"""Issuer holdings collection; snapshots are never represented as historical data."""
from pathlib import Path
import requests
import re
import hashlib
import json
from datetime import datetime,timezone
import pandas as pd
from concurrent.futures import ThreadPoolExecutor,as_completed
from io import StringIO,BytesIO
import html
import zipfile

VANGUARD={'VOO':'voo/vanguard-sp-500-etf','VTI':'vti/vanguard-total-stock-market-etf','VT':'vt/vanguard-total-world-stock-etf',
          'VUG':'vug/vanguard-growth-etf','VTV':'vtv/vanguard-value-etf','VB':'vb/vanguard-small-cap-etf',
          'VYM':'vym/vanguard-high-dividend-yield-etf','VIG':'vig/vanguard-dividend-appreciation-etf',
          'VOOG':'voog/vanguard-sp-500-growth-etf','VXUS':'vxus/vanguard-total-international-stock-etf',
          'VEA':'vea/vanguard-ftse-developed-markets-etf','VWO':'vwo/vanguard-ftse-emerging-markets-etf',
          'VBR':'vbr/vanguard-small-cap-value-etf'}
ISHARES={
 'IVV':('us','239726/ishares-core-sp-500-etf'), 'ITOT':('us','239724/ishares-core-sp-total-us-stock-market-etf'),
 'DGRO':('us','264623/ishares-core-dividend-growth-etf'), 'DVY':('us','239500/ishares-select-dividend-etf'),
 'QUAL':('us','256101/ishares-msci-usa-quality-factor-etf'), 'IEMG':('us','244050/ishares-core-msci-emerging-markets-etf'),
 'MTUM':('us','251614/ishares-msci-usa-momentum-factor-etf'), 'USMV':('us','239695/ishares-msci-usa-minimum-volatility-etf'),
 'IWDA':('uk/individual/en','251882/ishares-msci-world-ucits-etf-acc-fund'),
 'ISAC':('uk/individual/en','251850/ishares-msci-acwi-ucits-etf'),
 'EIMI':('uk/individual/en','264659/ishares-msci-emerging-markets-imi-ucits-etf'),
 'IWQU':('uk/professionals/en','270054/iwqu'),
 'IWMO':('uk/individual/en','270051/ishares-msci-world-momentum-factor-ucits-etf'),
 'CSPX':('uk/individual/en','253743/ishares-sp-500-b-ucits-etf-acc-fund'),
 'CNDX':('uk/individual/en','253741/ishares-nasdaq-100-ucits-etf'),
 'WSML':('uk/individual/en','296576/ishares-msci-world-small-cap-ucits-etf'),
}

def collect_vanguard(ticker,slug):
    pageurl='https://advisors.vanguard.com/investments/products/'+slug
    try:
        page=DEST/(ticker+'-page.html')
        if page.exists():page_text=page.read_text(encoding='utf-8')
        else:
            r,page=get(pageurl,ticker+'-page.html');page_text=r.text
        marker='window.__INITIAL_FUND_DATA__ = '
        p=page_text.find(marker)
        obj,_=json.JSONDecoder().raw_decode(page_text[p+len(marker):])
        assert obj['fundIdentifier']==ticker,(ticker,obj)
        port=obj['portId']
        url=f'https://advisors.vanguard.com/investments/products/api/funds/{port}/holdings/latest'
        path=DEST/(ticker+'-latest.json')
        if path.exists():j=json.loads(path.read_text(encoding='utf-8'))
        else:r,path=get(url,ticker+'-latest.json');j=r.json()
        date=j['latestEffectiveDate'];book=j[date]
        rows=[]
        for kind,items in book.items():
            if not isinstance(items,list) or kind in {'allocationToUnderlyingFunds','shortTermReservesMoneyMarket'}:continue
            for x in items:
                if not isinstance(x,dict) or 'percentOfFunds' not in x:continue
                try:weight=float(x['percentOfFunds'])/100
                except (TypeError,ValueError):continue
                rows.append(dict(etf=ticker,issuer_name=x.get('holdingName',''),security_id=x.get('cusip') or x.get('sedol') or x.get('ticker',''),
                                 ticker=x.get('ticker',''),cusip=x.get('cusip',''),sedol=x.get('sedol',''),
                                 sector='',industry=x.get('sector',''),country=x.get('country',''),currency=x.get('currency',''),
                                 weight=weight,as_of=date,source_url=url,
                                 asset_class=kind,coverage_type='issuer_full_portfolio'))
        return rows,dict(etf=ticker,status='complete_issuer',as_of=date,source_url=url,file=path.name,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(rows),port_id=port)
    except Exception as e:return [],dict(etf=ticker,status='unavailable',source_url=pageurl,error=str(e))

def csv_book(ticker,text,url):
    lines=text.lstrip('\ufeff').splitlines()
    header=next((i for i,l in enumerate(lines) if l.startswith('Ticker,') or l.startswith('"Ticker",')),None)
    if header is None:raise ValueError('No holdings CSV header')
    date=''
    for line in lines[:header]:
        if 'Fund Holdings as of' in line or 'Holdings as of' in line:
            value=line.split(',',1)[1].replace('"','').strip()
            for pt,en in [('jan.','Jan'),('fev.','Feb'),('mar.','Mar'),('abr.','Apr'),('mai.','May'),('jun.','Jun'),('jul.','Jul'),('ago.','Aug'),('set.','Sep'),('out.','Oct'),('nov.','Nov'),('dez.','Dec')]:value=value.replace(pt,en)
            date=str(pd.to_datetime(value).date())
    # CSV footnotes may have many fields; skip malformed trailing commentary.
    frame=pd.read_csv(StringIO('\n'.join(lines[header:])),on_bad_lines='skip',dtype=str)
    rows=[]
    brazil=ticker.endswith('11')
    def num(v):
        s=str(v).replace('%','')
        return float(s.replace('.','').replace(',','.')) if brazil else float(s.replace(',',''))
    # The issuer percentage column is rounded (often to two decimal places).
    # Reconstruct precision from the complete disclosed net market-value book.
    market_values=pd.to_numeric(frame.get('Market Value',pd.Series(dtype=float)).map(lambda v:num(v) if isinstance(v,str) and re.match(r'^[-\d.,]+$',v) else float('nan')),errors='coerce')
    market_nav=float(market_values.sum())
    for x in frame.to_dict('records'):
        wc='Market Weight' if 'Market Weight' in x else 'Weight (%)'
        try:
            published=num(x[wc])/100
            w=num(x['Market Value'])/market_nav if market_nav>0 else published
        except:continue
        if not isinstance(x.get('Name'),str):continue
        rows.append(dict(etf=ticker,issuer_name=x['Name'],security_id=x.get('ISIN') or x.get('CUSIP') or x.get('Ticker',''),
                         ticker=x.get('Ticker',''),cusip=x.get('CUSIP',''),sedol=x.get('SEDOL',''),
                         sector=x.get('Sector',''),industry='',country=x.get('Location',''),currency=x.get('Market Currency',''),
                         weight=w,published_weight=published,as_of=date,source_url=url,asset_class=x.get('Asset Class',''),coverage_type='issuer_full_portfolio'))
    if not rows:raise ValueError('No numerical holding rows')
    return rows,date

def collect_ishares(ticker,location,slug):
    pageurl=f'https://www.ishares.com/{location}/products/{slug}'
    try:
        r,page=get(pageurl,ticker+'-page.html')
        urls=re.findall(r'https[^"<>\\ ]+(?:latest-holdings\.csv|\.ajax\?[^"<> ]+)',html.unescape(r.text))
        urls=[u.replace('\\u0026','&') for u in urls if 'holdings' in u.lower() or 'fileType=csv' in u]
        relcsv=re.findall(r'href="([^"]+latest-holdings\.csv)"',html.unescape(r.text))
        urls+=['https://www.ishares.com'+u if u.startswith('/') else u for u in relcsv]
        if not urls:
            # New-page JSON-LD contains canonical URL even if requested slug differs.
            m=re.search(r'"contentUrl":"([^"]+latest-holdings\.csv)"',r.text)
            if m:urls=[m.group(1).replace('\\u0026','&')]
        if not urls:
            # Legacy UK exports expose a data URL as a relative link.
            rel=re.findall(r'[^"<> ]+\.ajax[^"<> ]*',html.unescape(r.text))
            urls=['https://www.ishares.com'+u for u in rel if u.startswith('/') and 'csv' in u.lower()]
        if not urls:
            canonical=re.search(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"',r.text)
            base=canonical.group(1) if canonical else pageurl
            urls=[base.rstrip('/')+'/latest-holdings.csv']
        errors=[]
        for url in list(dict.fromkeys(urls))[:4]:
            try:
                rr,path=get(url,ticker+'-latest.csv')
                rows,date=csv_book(ticker,rr.content.decode('utf-8-sig',errors='replace'),url)
                return rows,dict(etf=ticker,status='complete_issuer',as_of=date,source_url=url,file=path.name,
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(rows))
            except Exception as exc:errors.append(str(exc))
        raise ValueError('; '.join(errors))
    except Exception as e:return [],dict(etf=ticker,status='unavailable',source_url=pageurl,error=str(e))

def collect_core():
    tasks=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks+=[pool.submit(collect_vanguard,t,s) for t,s in VANGUARD.items()]
        tasks+=[pool.submit(collect_ishares,t,*s) for t,s in ISHARES.items()]
        allrows=[];records=[]
        for task in as_completed(tasks):
            rows,record=task.result();allrows+=rows;records.append(record)
            print(record['etf'],record['status'],len(rows),record.get('as_of',''),flush=True)
            pd.DataFrame(allrows).to_csv(DEST/'holdings-stage.csv',index=False)
            (DEST/'manifest-stage.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    return allrows,records

COUNTRIES=dict(US='United States',GB='United Kingdom',JP='Japan',CA='Canada',FR='France',DE='Germany',CH='Switzerland',AU='Australia',CN='China',TW='Taiwan',HK='Hong Kong',KR='Korea (South)',IN='India',NL='Netherlands',SE='Sweden',DK='Denmark',ES='Spain',IT='Italy',FI='Finland',NO='Norway',BE='Belgium',IE='Ireland',AT='Austria',SG='Singapore',IL='Israel',NZ='New Zealand',BR='Brazil',ZA='South Africa',MX='Mexico',SA='Saudi Arabia',ID='Indonesia',TH='Thailand',MY='Malaysia',AE='United Arab Emirates',QA='Qatar',KW='Kuwait',PH='Philippines',TR='Turkey',CL='Chile',CO='Colombia',PE='Peru',GR='Greece',PL='Poland',PT='Portugal',HU='Hungary',CZ='Czech Republic',EG='Egypt',RU='Russian Federation',PK='Pakistan',RO='Romania',LU='Luxembourg',KY='Cayman Islands',BM='Bermuda',IS='Iceland',MT='Malta',CY='Cyprus',MO='Macau',JE='Jersey',GG='Guernsey',IM='Isle of Man',UY='Uruguay',AR='Argentina',MC='Monaco',VN='Vietnam',BD='Bangladesh',KZ='Kazakhstan',NG='Nigeria',MA='Morocco')

def issuer_name(value):
    s=str(value).upper()
    s=re.sub(r'\b(CLASS|CL)\s+[A-Z0-9]+\b','',s)
    s=re.sub(r'\b(INCORPORATED|CORPORATION|COMPANY|LIMITED|HOLDINGS|HOLDING|INC|CORP|CO|LTD|PLC|ADR|ADS|ORD|COMMON|STOCK|REGISTERED|REG|SA|AG|SE|NV)\b','',s)
    s=re.sub(r'[^A-Z0-9]','',s)
    return s

def normalize_and_publish():
    rows=[];records=[]
    for ticker,slug in VANGUARD.items():
        a,b=collect_vanguard(ticker,slug);rows+=a;records.append(b)
    # Reparse exact raw files, not possibly incomplete parallel-stage outputs.
    recmap={}
    for file in ['manifest-stage.json','ucits-manifest.json']:
        if (DEST/file).exists():recmap.update({x['etf']:x for x in json.loads((DEST/file).read_text())})
    for ticker in ISHARES:
        path=DEST/(ticker+'-latest.csv')
        if not path.exists():continue
        try:
            source=recmap.get(ticker,{}).get('source_url','')
            a,date=csv_book(ticker,path.read_text(encoding='utf-8-sig'),source)
            rows+=a;records.append(dict(etf=ticker,status='complete_issuer',as_of=date,source_url=source,file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),rows=len(a)))
        except Exception as e:records.append(dict(etf=ticker,status='unavailable',error=str(e)))
    for file in ['extra-rows.csv']:
        if (DEST/file).exists():rows+=pd.read_csv(DEST/file).fillna('').to_dict('records')
    if (DEST/'extra-manifest.json').exists():records+=json.loads((DEST/'extra-manifest.json').read_text())
    frame=pd.DataFrame(rows).fillna('')
    frame['asset_class']=frame.asset_class.replace({'Renda Variável':'Equity','Equities':'Equity','equity':'Equity'})
    frame['country']=frame.country.map(lambda x:COUNTRIES.get(x,x))
    frame['country']=frame.country.replace({'Korea (South)':'Korea (South)','South Korea':'Korea (South)','Korea':'Korea (South)','Brasil':'Brazil','-':'','--':''})
    frame['sector']=frame.sector.replace({'Communication':'Communication Services','Energia':'Energy','Materiais':'Materials','Produtos financeiros':'Financials','Consumo não-cíclico':'Consumer Staples','Consumo cíclico':'Consumer Discretionary','Serviços de utilidade pública':'Utilities','Saúde':'Health Care','Industriais':'Industrials','Tecnologia da informação':'Information Technology','Imóveis':'Real Estate','Comunicações':'Communication Services','Caixa e/ou Derivativos':'Cash and Derivatives','Cash and/or Derivatives':'Cash and Derivatives','-':'','--':''})
    # Exact security keys allow primary-source crossmatching. Conflicting
    # classifications/currencies remain unresolved rather than selected by guess.
    frame['norm_issuer']=frame.issuer_name.map(issuer_name)
    frame['norm_ticker']=frame.ticker.map(lambda x:re.sub(r'[^A-Z0-9]','',str(x).upper()).lstrip('0'))
    frame['key_tc']=[str(t)+'|'+str(country) for t,country in zip(frame.norm_ticker,frame.country)]
    frame['key_tn']=[str(t)+'|'+str(name) for t,name in zip(frame.norm_ticker,frame.norm_issuer)]
    frame['key_nc']=[str(name)+'|'+str(country) for name,country in zip(frame.norm_issuer,frame.country)]
    equity=frame.asset_class.isin(['equity','Equity','Renda Variável'])
    for attribute in ['industry','sector','currency']:
        for key in ['cusip','sedol','key_tc','key_tn','key_nc']:
            good=frame.loc[equity&frame[attribute].ne('')&frame[key].ne('')]
            grouped=good.groupby(key)[attribute].agg(['first','nunique'])
            mapping=grouped.loc[grouped['nunique'].eq(1),'first'].to_dict()
            missing=equity&frame[attribute].eq('')
            fill=frame.loc[missing,key].map(mapping).fillna('')
            frame.loc[missing,attribute]=fill
    industrymap={}
    # Vanguard labels GICS sub-industry as 'sector'. Map sub-industry to broad
    # sector only when exact primary security matches establish one sector.
    vg=frame.etf.isin(VANGUARD)&frame.industry.ne('')&frame.sector.ne('')
    for industry,g in frame.loc[vg].groupby('industry'):
        values=g.sector.unique()
        if len(values)==1:industrymap[industry]=values[0]
    missing=frame.sector.eq('')
    frame.loc[missing,'sector']=frame.loc[missing,'industry'].map(industrymap).fillna('')
    frame.loc[equity&frame.country.eq('United States')&frame.currency.eq(''),'currency']='USD'
    frame.loc[frame.asset_class.isin(['shortTermReserves','derivatives']),'sector']='Cash and Derivatives'
    frame['issuer_id']=['issuer:'+issuer_name(name) if str(name).strip() else 'unknown:'+str(t)+':'+str(i)
                        for i,(t,name,country) in enumerate(zip(frame.etf,frame.issuer_name,frame.country))]
    frame['industry']=frame.industry.replace({'-':'','--':''})
    frame['currency']=frame.currency.replace({'-':'','--':''})
    output_columns=['etf','issuer_id','issuer_name','security_id','sector','industry','country','currency','weight','as_of','source_url','coverage_type','asset_class','ticker','cusip','sedol']
    temp=DEST/'holdings-next.csv';frame[output_columns].to_csv(temp,index=False);temp.replace(DEST/'holdings.csv')
    universe=pd.read_csv(ROOT/'data/universe.csv')
    coverage=[];by={x['etf']:x for x in records}
    for row in universe.to_dict('records'):
        ticker=row['ticker'];g=frame.loc[frame.etf.eq(ticker)];positive=g.weight.clip(lower=0)
        equity=g.asset_class.isin(['equity','Equity'])
        known_company=equity&g.issuer_name.ne('')
        rec=dict(etf=ticker,status='complete_issuer' if len(g) else 'not_recovered',as_of=str(g.as_of.iloc[0]) if len(g) else '',rows=len(g),
                 weight_sum=float(g.weight.sum()),gross_weight_sum=float(g.weight.abs().sum()),
                 equity_weight=float(g.loc[equity,'weight'].sum()),company_known_weight=float(positive.loc[known_company].sum()),
                 sector_known_weight=float(positive.loc[g.sector.ne('')].sum()),country_known_weight=float(positive.loc[g.country.ne('')].sum()),
                 currency_known_weight=float(positive.loc[g.currency.ne('')].sum()),industry_known_weight=float(positive.loc[g.industry.ne('')].sum()),
                 company_unknown_weight=float(positive.loc[equity&~known_company].sum()),
                 sector_unknown_weight=float(positive.loc[g.sector.eq('')].sum()),country_unknown_weight=float(positive.loc[g.country.eq('')].sum()),
                 currency_unknown_weight=float(positive.loc[g.currency.eq('')].sum()),industry_unknown_weight=float(positive.loc[g.industry.eq('')].sum()),source_url=by.get(ticker,{}).get('source_url',''),
                 note='Current issuer snapshot. No historical point-in-time certification. Industry missing where not disclosed; currency is security market currency, not revenue currency.' if len(g) else 'Complete issuer holdings not recovered yet; never replaced with top ten or equivalent ETF.')
        coverage.append(rec)
    cov=pd.DataFrame(coverage);temp=DEST/'coverage-next.csv';cov.to_csv(temp,index=False);temp.replace(DEST/'coverage.csv')
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),source_records=records,
                  holdings_sha256=hashlib.sha256((DEST/'holdings.csv').read_bytes()).hexdigest(),
                  coverage_sha256=hashlib.sha256((DEST/'coverage.csv').read_bytes()).hexdigest(),
                  transformations=['Exclude Vanguard allocationToUnderlyingFunds duplicate of short-term reserves','Issuer ID groups normalized same issuer name and share classes; unresolved names not guessed','Sector/currency transferred only on exact ticker and country match; sub-industry mapped when matched primary rows unanimously identify sector','US domestic equity market currency USD only; no foreign country-to-currency inference'])
    temp=DEST/'manifest-next.json';temp.write_text(json.dumps(manifest,indent=2),encoding='utf-8');temp.replace(DEST/'manifest.json')
    pd.DataFrame(sorted(industrymap.items()),columns=['industry','sector']).to_csv(DEST/'industry_sector_crosswalk.csv',index=False)
    print(cov[['etf','status','rows','weight_sum','sector_unknown_weight','country_unknown_weight','currency_unknown_weight']].to_string(index=False),flush=True)
    return frame,cov

CVM_FUNDS={'PIBB11':'06.323.688/0001-27','BOVA11':'10.406.511/0001-61','SMAL11':'10.406.600/0001-08',
           'GOVE11':'11.184.136/0001-15','BRAX11':'11.455.378/0001-04','FIND11':'11.961.094/0001-81',
           'DIVO11':'13.416.245/0001-46','BBSD11':'17.817.528/0001-50','IVVB11':'19.909.560/0001-91',
           'BOVV11':'21.407.758/0001-19','BBOV11':'34.606.480/0001-50','NASD11':'35.578.672/0001-63',
           'WRLD11':'42.280.262/0001-05','AUVP11':'61.273.759/0001-32','VWRA11':'61.689.798/0001-15',
           'BEST11':'61.950.414/0001-76'}

def collect_extras():
    out=[];records=[]
    url='https://www.blackrock.com/br/products/251816/ishares-ibovespa-fundo-de-ndice-fund/1506433276998.ajax?fileType=csv&fileName=BOVA11_holdings&dataType=fund'
    bova,date=csv_book('BOVA11',(DEST/'BOVA11-latest.csv').read_text(encoding='utf-8-sig'),url)
    # Preserve this more recent issuer file for BOVA; use its exact Brazilian
    # tickers for cross-source names and sectors of other CVM-listed holdings.
    out+=bova
    records.append(dict(etf='BOVA11',status='complete_issuer',as_of=date,source_url=url,file='BOVA11-latest.csv',rows=len(bova)))
    cvmurl='https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/cda_fi_202609.zip'
    z=zipfile.ZipFile(DEST/'cvm-cda-202609.zip')
    all_cvm=pd.read_csv(z.open('cda_fie_202609.csv'),sep=';',encoding='latin1',dtype=str).fillna('')
    all_cvm=all_cvm.loc[all_cvm.TP_FUNDO_CLASSE.eq('CLASSES FIIM')]
    bova_names={r['ticker']:r for r in bova}
    for etf,cnpj in CVM_FUNDS.items():
        if etf=='BOVA11':continue
        g=all_cvm.loc[all_cvm.CNPJ_FUNDO_CLASSE.eq(cnpj)].copy()
        if g.empty:
            records.append(dict(etf=etf,status='unavailable',source_url=cvmurl,error='No September 2026 CDA rows for CNPJ '+cnpj));continue
        pl=pd.to_numeric(g.VL_PATRIM_LIQ).unique()
        if len(pl)!=1:raise ValueError('Ambiguous fund NAV: '+etf)
        g.to_csv(DEST/(etf+'-cvm-202609.csv'),index=False)
        before=len(out)
        for x in g.to_dict('records'):
            try:weight=float(x['VL_MERC_POS_FINAL'])/float(pl[0])
            except:continue
            if weight==0:continue
            application=x['TP_APLIC'];tick=x['CD_ATIVO'].strip()
            if application=='Valores a pagar':weight=-abs(weight)
            is_stock=application.startswith('Ações') or application.startswith('Certificado ou recibo')
            if is_stock and tick:
                peer=bova_names.get(tick,{})
                # The administrator reports a ticker, even when issuer name is
                # blank. Group B3 share classes by the four-letter issuer root.
                company=peer.get('issuer_name') or x['EMISSOR'] or tick[:4]
                sector=peer.get('sector','')
                out.append(dict(etf=etf,issuer_name=company,security_id=tick,ticker=tick,cusip='',sedol='',sector=sector,industry='',country='Brazil',currency='BRL',weight=weight,as_of=x['DT_COMPTC'],source_url=cvmurl,asset_class='Equity',coverage_type='regulator_full_portfolio'))
            elif application=='Investimento no Exterior':
                child='IVV' if etf=='IVVB11' and 'ISHARES CORE SP500' in x['EMISSOR'] else 'VT' if tick=='VT' else ''
                if child:
                    if child=='VT':childrows,_=collect_vanguard('VT',VANGUARD['VT'])
                    else:
                        u='https://www.ishares.com/us/products/239726/ishares-core-s-p-500-etf/latest-holdings.csv'
                        childrows,_=csv_book('IVV',(DEST/'IVV-latest.csv').read_text(encoding='utf-8-sig'),u)
                    for h in childrows:
                        r=dict(h);r.update(etf=etf,weight=weight*h['weight'],source_url=cvmurl+' | '+h['source_url'],coverage_type='regulator_feeder_recursively_expanded_current_snapshots')
                        out.append(r)
                else:
                    out.append(dict(etf=etf,issuer_name=x['EMISSOR'] or tick,security_id=tick,ticker=tick,cusip='',sedol='',sector='',industry='',country='',currency='',weight=weight,as_of=x['DT_COMPTC'],source_url=cvmurl,asset_class='Opaque underlying ETF',coverage_type='regulator_unexpanded_fund_position'))
            else:
                cash=application in {'Disponibilidades','Valores a receber','Valores a pagar','Operações Compromissadas','Títulos Públicos'}
                out.append(dict(etf=etf,issuer_name=x['EMISSOR'] or x['DS_ATIVO'] or application,security_id=tick,ticker=tick,cusip='',sedol='',sector='Cash and Derivatives' if cash else '',industry='',country='Brazil' if cash else '',currency='BRL' if cash else '',weight=weight,as_of=x['DT_COMPTC'],source_url=cvmurl,asset_class='Cash' if cash else application,coverage_type='regulator_full_portfolio'))
        records.append(dict(etf=etf,status='complete_regulator',as_of='2026-09-30',source_url=cvmurl,file=etf+'-cvm-202609.csv',cnpj=cnpj,rows=len(out)-before,
                            underlying_note='Feeder expansion uses current underlying snapshot; mixed dates, not historical certification' if etf in {'IVVB11','WRLD11'} else ''))
    # SPY official full file, converted from original XLSX without changing data.
    spyfile=DEST/'SPY-converted.csv'
    if spyfile.exists():
        data=pd.read_csv(spyfile,header=4,dtype=str).fillna('')
        for x in data.to_dict('records'):
            try:weight=float(x['Weight'])/100
            except:continue
            out.append(dict(etf='SPY',issuer_name=x['Name'],security_id=x['Identifier'],ticker=x['Ticker'],cusip=x['Identifier'],sedol=x['SEDOL'],sector='',industry='',country='',currency=x['Local Currency'],weight=weight,as_of='2026-10-29',source_url='https://www.ssga.com/us/en/individual/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx',asset_class='Equity' if x['Ticker'] else 'Cash',coverage_type='issuer_full_portfolio'))
        records.append(dict(etf='SPY',status='complete_issuer',as_of='2026-10-29',source_url='https://www.ssga.com/us/en/individual/etfs/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx',file='SPY.xlsx'))
    pd.DataFrame(out).to_csv(DEST/'extra-rows.csv',index=False)
    (DEST/'extra-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    return out,records

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'data/v2/holdings'
DEST.mkdir(parents=True,exist_ok=True)

def get(url,name):
    response=requests.get(url,timeout=35,headers={'User-Agent':'Mozilla/5.0','Accept':'*/*'})
    response.raise_for_status()
    path=DEST/name
    path.write_bytes(response.content)
    return response,path

def probe():
    for name,url in [('ivv','https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf'),('voo','https://advisors.vanguard.com/investments/products/voo/vanguard-sp-500-etf')]:
        r,path=get(url,name+'-page.html')
        s=r.text
        print(name,r.status_code,len(s),r.url,flush=True)
        for token in ['.ajax','fileType','asOfDate','holdingsData','holdings','api.vanguard']:
            hits=list(re.finditer(re.escape(token),s))
            print(token,len(hits),flush=True)
            for m in hits[:8]:print(s[max(0,m.start()-100):m.end()+200],flush=True)

def probe_vanguard():
    s=(DEST/'voo-page.html').read_text(encoding='utf-8')
    for pattern in ['<script[^>]+src="([^"]+)"','https?[^"<> ]+','portfolio-holding','holdings']:
        hits=list(re.finditer(pattern,s))
        print('PATTERN',pattern,len(hits))
        for m in hits[-12:]:print(s[max(0,m.start()-60):m.end()+150])

def probe_vanguard_data():
    s=(DEST/'voo-page.html').read_text(encoding='utf-8')
    for token in ['__INITIAL_FUND_DATA__','<base','holdingsDate','holdingsData']:
        p=s.find(token)
        print(token,s[p:p+500])
    pos=s.find('window.__INITIAL_FUND_DATA__ = ')
    obj,_=json.JSONDecoder().raw_decode(s[pos+len('window.__INITIAL_FUND_DATA__ = '):])
    print('DATA',obj.keys())
    (DEST/'VOO-initial.json').write_text(json.dumps(obj,indent=2),encoding='utf-8')
    for u in ['https://advisors.vanguard.com/investments/product-details/assets/index-CQBMFSOn.js','https://advisors.vanguard.com/investments/products/voo/assets/index-CQBMFSOn.js','https://advisors.vanguard.com/investments/assets/index-CQBMFSOn.js']:
        r=requests.get(u,timeout=20)
        print('JS',u,r.status_code,len(r.content),r.text[:40])
        if r.status_code==200 and 'javascript' in r.headers.get('Content-Type',''):
            (DEST/'vanguard-main.js').write_text(r.text,encoding='utf-8')
            for token in ['holdings','api.vanguard','portfolio-holding','https://']:
                hits=list(re.finditer(re.escape(token),r.text));print(token,len(hits))
                for m in hits[:12]:print(r.text[max(0,m.start()-100):m.end()+200])

if __name__=='__main__':normalize_and_publish()
