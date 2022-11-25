from appservicecore.api_service import APIService, APIServiceRequest

if __name__ == "__main__":
    service_request = APIServiceRequest()
    service_request.name('service.alertmanager')
    service_request.port(1111)
    service_request.add_packages('monitoring.api.alertmanager*')
    APIService(request=service_request).start()
