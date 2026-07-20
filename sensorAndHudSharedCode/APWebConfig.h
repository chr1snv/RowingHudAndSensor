#ifndef APWebConfig
#define APWebConfig

#include "esp_http_server.h"
//#include "esp_http_client.h"
#include "HTTPClient.h"

httpd_handle_t local_httpd = NULL;

#include "localWebpage.h"

//ascii to int reverse iteration for n characters
//input is end of number (1's place)
//counts up in significance (x10), decrementing string index from start index
uint16_t atoir_n( const char * c, uint8_t n ){
	uint16_t accum = 0;
	uint16_t mult = 1;
	//Serial.print( "atoir_n d ");
	for( uint8_t i = 0; i < n; ++i ){
		char d = c[-i];
		if( d >= '0' && d <= '9' )
			accum += (d - '0')*mult;
		else
			break;
		mult *= 10;
		//Serial.print( d ); Serial.print(" acum ");Serial.print(accum);Serial.print(" d ");
	}
	//Serial.print(" accum ");Serial.println(accum);
	return accum;
}


static esp_err_t index_handler(httpd_req_t *req){
	httpd_resp_set_type(req, "text/html");
	return httpd_resp_send(req, (const char *)INDEX_HTML, strlen(INDEX_HTML));
}

static esp_err_t settings_handler(httpd_req_t *req){
	fillSettingsString(lastCsiInfoStr);

	httpd_resp_set_type(req, "text/html");
	return httpd_resp_send(req, lastCsiInfoStr, SETTINGS_RESPONSE_LENGTH);
}

//https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/protocols/esp_http_server.html
static esp_err_t cmd_post_handler( httpd_req_t * req ){
	char content[CMD_BUFF_MAX_LEN];
	size_t recv_size = min( (int)(req->content_len), CMD_BUFF_MAX_LEN );
	Serial.print("recv_size ");Serial.println( recv_size );

	int ret = httpd_req_recv(req, &content[0], recv_size);
	if( ret <= 0 ){
		if( ret == HTTPD_SOCK_ERR_TIMEOUT ){
			httpd_resp_send_408(req);
		}
		return ESP_FAIL;
	}

	Serial.print("recvd from lclWebPg ");
	Serial.println( content );

	uint8_t doCmdRes = doCommandsInRecievedData( recv_size, content );
	if( doCmdRes < 1 )
		return httpd_resp_send_500(req); //did not understand or was not able to handle the requested cmd
	Serial.print("doCmdRes " ); Serial.print(doCmdRes);
	const char resp[] = "cmd recieved";
	httpd_resp_send( req, resp, HTTPD_RESP_USE_STRLEN );
	return ESP_OK;
}


void startLocalWebServer(){
	if( local_httpd != NULL )
		return;

	httpd_config_t config = HTTPD_DEFAULT_CONFIG();
	config.server_port = 80;
	httpd_uri_t index_uri = {
		.uri       = "/",
		.method    = HTTP_GET,
		.handler   = index_handler,
		.user_ctx  = NULL
	};

	httpd_uri_t settings_uri = {
		.uri       = "/settings",
		.method    = HTTP_GET,
		.handler   = settings_handler,
		.user_ctx  = NULL
	};

	httpd_uri_t cmd_uri = {
		.uri       = "/action",
		.method    = HTTP_POST,
		.handler   = cmd_post_handler,
		.user_ctx  = NULL
	};
	if (httpd_start(&local_httpd, &config) == ESP_OK) {
		httpd_register_uri_handler(local_httpd, &index_uri);
		httpd_register_uri_handler(local_httpd, &cmd_uri);
		httpd_register_uri_handler(local_httpd, &settings_uri);
	Serial.println("Local webpage ready! ");
	}
}


int startAPWebConfig(){
  espNowReady = false;

  Serial.println("startAPWebConfig");

  startLocalWebServer();

  return 1;
}

#endif