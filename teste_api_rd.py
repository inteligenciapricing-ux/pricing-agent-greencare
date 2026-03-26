import requests
import json

# ============================================================
# CONFIGURAÇÃO
# ============================================================

URL = "https://www.drogasil.com.br/api/next/busca/graphql"

COOKIE = "mcpId=af4ac2e8abe06f8601; _sfid_9140={%22anonymousId%22:%22af4ac2e8abe06f8601%22%2C%22consents%22:[]}; kwai_uuid=0c102b3166dbe1b5e61ea28eae48363c; r2UserId=1761588101019484; consent_sent_flag=true; rrsession=ae10fd1aafb7376d5662c; OptanonAlertBoxClosed=2025-10-27T18:01:54.119Z; _fbp=fb.2.1761588114559.575964563307829006; _tt_enable_cookie=1; _ttp=01K8KDAX4X9DY4GNQ3SB0N2Z1E_.tt.2; _pin_unauth=dWlkPU56TmxNbU00T0dRdE56QTBPUzAwTkdaakxXSmlPVEl0TXpNeU9XUTFPR016T1dOaQ; _ga=GA1.1.837587441.1761588115; blueID=3ad6c7e4-7550-426d-8d76-d6d88bd674cd; _hjSessionUser_557741=eyJpZCI6ImMxNTE2NTliLTRhNWQtNWIxYy04YTBjLTk0YTU5ZjJkNjlhNiIsImNyZWF0ZWQiOjE3NjE1ODgxMTQ3NDYsImV4aXN0aW5nIjp0cnVlfQ==; analytic_id=1763123653691192; cto_bundle=ddzril94anFaRU04UDFFYzZXZjJzbmwwM2RoNzZhTm1TWExZSTZEcEV2WFU3cnQ0YmdjV3AlMkJ1NjVDakpaUFpTWGY1VjVGczZPTlFYa3JrdlRmZ2t0aWNIeklOenVFTDhQJTJCdjlRZU1ndlBSNFdKaXZpUzg1TUJCenBrUkp1c0RndGNJYkNjUCUyQnQyZVB6VXh3amRENnlrT1hYckEzMVNsaUw1R2JCMVhUNjZrQjRJR2clM0Q; fs_uid=#o-23XT8Q-na1#16f21993-5b63-4e93-9ee7-d0bfa2687da8:293551e2-77c0-4f48-b452-e65d5c92e0d7:1763990430037::2#/1794056339; guesttoken=87c7ce3f-40b9-4434-91eb-6f65040ce521; carttoken=87c7ce3f-40b9-4434-91eb-6f65040ce521; _gcl_au=1.1.275926598.1773446366; user_unic_ac_id=c2296e86-7677-1216-01f0-25f017292026; AwinChannelCookie=other; RKT=false; blueULC=blue; _ALGOLIA_USER_TOKEN_=anonymous-d6721c60-f39d-4bcc-9e30-651ff5c289d2; device_info=MjU2MHwxMDgwfGVuLVVTfFdpbjMy; _gcl_gs=2.1.k1$i1773669275$u198814586; _k_gid_collect=1; _k_cp=1; origem=adwords; advcake_url=https%3A%2F%2Fwww.drogasil.com.br%2Fcanabidiol-mantecorp-23-75mg-gotas-10ml.html%3Fgad_source%3D1%26gad_campaignid%3D17702998466%26gbraid%3D0AAAAADod4VXrDTvtQzicZbjWoiP5v7UQ-%26gclid%3DEAIaIQobChMIiJ22wIqekwMVREFIAB1QPhjrEAAYAyAAEgJ_OPD_BwE; advcake_trackid=b31c29ad-8b3c-cdfd-9631-dbb63d4fedb1; advcake_utm_content=google; advcake_utm_campaign=google; _gcl_aw=GCL.1773669291.EAIaIQobChMIiJ22wIqekwMVREFIAB1QPhjrEAAYAyAAEgJ_OPD_BwE; _hjSession_557741=eyJpZCI6IjhlMGI0NmRlLTAzNWItNDE4My05YWI0LTQyNzAxM2Q5YTVjMyIsImMiOjE3NzM3MDI1MDUyMjcsInMiOjAsInIiOjAsInNiIjowLCJzciI6MCwic2UiOjAsImZzIjowLCJzcCI6MH0=; _dd_s=aid=116641c3-023c-4eff-a678-79134950ae72&rum=0&expire=1773705958717; _ga_5J2QJPHWJP=GS2.1.s1773704961$o19$g1$t1773705059$j54$l0$h0; OptanonConsent=isGpcEnabled=0&datestamp=Mon+Mar+16+2026+20%3A50%3A59+GMT-0300+(Brasilia+Standard+Time)&version=202510.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=67c359cf-6748-48d9-9c06-c120332252e9&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0002%3A1%2CC0003%3A1%2CC0004%3A1%2CC0008%3A1&AwaitingReconsent=false&intType=1&geolocation=BR%3BSP; _evga_d898={%22uuid%22:%22af4ac2e8abe06f8601%22}; ttcsid=1773704961528::fFirCVr0nlsoSY9I3knS.15.1773705059846.0; ttcsid_CC8EA5RC77UB2PF18I5G=1773704961527::6KLqbG-J_zXpShgDJrN2.15.1773705059846.1"

HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://www.drogasil.com.br",
    "referer": "https://www.drogasil.com.br/",
    "user-agent": "Mozilla/5.0",
    "cookie": COOKIE
}

# ============================================================
# PAYLOAD DE TESTE
# ============================================================

PAYLOAD = {
    "operationName": "search",
    "variables": {
        "query": "canabidiol",
        "page": 1
    },
    "query": "query search($query:String,$page:Int){search(query:$query,page:$page){products{name}}}"
}

# ============================================================
# EXECUÇÃO
# ============================================================

def testar_api():

    print("\n==============================")
    print("TESTE API DROGASIL")
    print("==============================\n")

    try:

        response = requests.post(
            URL,
            headers=HEADERS,
            json=PAYLOAD,
            timeout=30
        )

        print("STATUS CODE:")
        print(response.status_code)

        print("\nRESPONSE HEADERS:")
        print(response.headers)

        print("\nRAW RESPONSE (primeiros 2000 caracteres):\n")
        print(response.text[:2000])

        try:
            data = response.json()

            print("\nJSON PARSEADO:\n")
            print(json.dumps(data, indent=2)[:4000])

        except:
            print("\nResposta não é JSON.")

    except Exception as e:

        print("\nERRO NA REQUISIÇÃO:")
        print(str(e))


if __name__ == "__main__":
    testar_api()