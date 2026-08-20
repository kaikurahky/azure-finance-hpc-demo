param name string
param location string
param tags object
param environmentName string
param registryName string
param applicationInsightsConnectionString string
param batchAccountEndpoint string
param batchPoolName string
param alwaysOnBatchPoolName string
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

var placeholderImage = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
var isPlaceholder = containerImage == placeholderImage
var appPort = 8000

resource environment 'Microsoft.App/managedEnvironments@2026-01-01' existing = {
  name: environmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: registryName
}

resource containerApp 'Microsoft.App/containerApps@2026-01-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        allowInsecure: false
        exposedPort: 0
        external: true
        targetPort: isPlaceholder ? 80 : appPort
        transport: 'Auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: isPlaceholder
        ? []
        : [
            {
              identity: 'system'
              server: registry.properties.loginServer
            }
          ]
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'finance-hpc-demo'
          image: containerImage
          env: [
            {
              name: 'PORT'
              value: string(isPlaceholder ? 80 : appPort)
            }
            {
              name: 'APP_ENV'
              value: 'production'
            }
            {
              name: 'CORS_ORIGINS'
              value: ''
            }
            {
              name: 'EXECUTION_MODE'
              value: isPlaceholder ? 'local' : 'azure'
            }
            {
              name: 'AZURE_BATCH_ACCOUNT_URL'
              value: 'https://${batchAccountEndpoint}'
            }
            {
              name: 'AZURE_BATCH_AUTOSCALE_POOL_ID'
              value: batchPoolName
            }
            {
              name: 'AZURE_BATCH_ALWAYS_ON_POOL_ID'
              value: alwaysOnBatchPoolName
            }
            {
              name: 'BATCH_TASK_DELAY_SECONDS'
              value: '180'
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsightsConnectionString
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: isPlaceholder
            ? []
            : [
                {
                  type: 'Liveness'
                  httpGet: {
                    path: '/healthz'
                    port: appPort
                    scheme: 'HTTP'
                  }
                  initialDelaySeconds: 5
                  periodSeconds: 10
                }
                {
                  type: 'Readiness'
                  httpGet: {
                    path: '/readyz'
                    port: appPort
                    scheme: 'HTTP'
                  }
                  initialDelaySeconds: 5
                  periodSeconds: 10
                }
              ]
        }
      ]
      scale: {
        cooldownPeriod: 300
        minReplicas: 0
        maxReplicas: 1
        pollingInterval: 30
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '30'
              }
            }
          }
        ]
      }
    }
  }
}

output id string = containerApp.id
output principalId string = containerApp.identity.principalId
output fqdn string = containerApp.properties.configuration.ingress.fqdn
