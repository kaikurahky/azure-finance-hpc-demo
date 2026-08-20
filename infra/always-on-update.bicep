targetScope = 'resourceGroup'

param containerImage string
param location string = resourceGroup().location

param containerAppName string = 'ca-finhpc-dev-28e5'
param containerEnvironmentName string = 'cae-finhpc-dev-28e5'
param containerRegistryName string = 'crfinhpcdev28e5'
param applicationInsightsName string = 'appi-finhpc-dev-28e5'
param batchAccountName string = 'bthfinhpcdev28e5'
param autoscalePoolName string = 'pool-finhpc-dev-28e5'
param alwaysOnPoolName string = 'pool-finhpc-alwayson-28e5'

var tags = {
  'app-onboard-skill': 'true'
  'app-onboard-session-id': '28e5fee0-6640-494e-b1b9-87306c722ed9'
  'created-at': '2026-08-18T09:58:00Z'
  environment: 'finhpc-dev-28e5'
  'deployed-by': 'Hideaki Kuraishi'
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

module batch './modules/batch.bicep' = {
  name: 'batch-always-on-update'
  params: {
    accountName: batchAccountName
    alwaysOnPoolName: alwaysOnPoolName
    autoscalePoolName: autoscalePoolName
    deployPool: true
    location: location
    tags: tags
  }
}

module containerApp './modules/container-app.bicep' = {
  name: 'container-app-always-on-update'
  params: {
    alwaysOnBatchPoolName: alwaysOnPoolName
    applicationInsightsConnectionString: applicationInsights.properties.ConnectionString
    batchAccountEndpoint: batch.outputs.accountEndpoint
    batchPoolName: autoscalePoolName
    containerImage: containerImage
    environmentName: containerEnvironmentName
    location: location
    name: containerAppName
    registryName: containerRegistryName
    tags: tags
  }
}

output alwaysOnPoolName string = alwaysOnPoolName
output containerAppName string = containerAppName
