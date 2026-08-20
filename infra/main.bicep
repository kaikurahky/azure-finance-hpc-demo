targetScope = 'subscription'

@minLength(1)
param environmentName string

param location string
param sessionId string
param deployedBy string
param createdAt string
param deployerObjectId string = ''

param resourceGroupName string
param containerEnvironmentName string
param containerAppName string
param containerRegistryName string
param batchAccountName string
param batchPoolName string
param alwaysOnBatchPoolName string
param storageAccountName string
param keyVaultName string
param logAnalyticsName string
param applicationInsightsName string

param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param deployBatchPool bool = false

var tags = {
  'app-onboard-skill': 'true'
  'app-onboard-session-id': sessionId
  'created-at': createdAt
  environment: environmentName
  'deployed-by': deployedBy
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module logAnalytics './modules/log-analytics.bicep' = {
  name: 'log-analytics'
  scope: resourceGroup
  params: {
    location: location
    name: logAnalyticsName
    tags: tags
  }
}

module applicationInsights './modules/application-insights.bicep' = {
  name: 'application-insights'
  scope: resourceGroup
  params: {
    location: location
    name: applicationInsightsName
    tags: tags
    workspaceResourceId: logAnalytics.outputs.id
  }
}

module storage './modules/storage.bicep' = {
  name: 'storage'
  scope: resourceGroup
  params: {
    location: location
    name: storageAccountName
    tags: tags
  }
}

module keyVault './modules/key-vault.bicep' = {
  name: 'key-vault'
  scope: resourceGroup
  params: {
    location: location
    name: keyVaultName
    tags: tags
  }
}

module containerRegistry './modules/container-registry.bicep' = {
  name: 'container-registry'
  scope: resourceGroup
  params: {
    location: location
    name: containerRegistryName
    tags: tags
  }
}

module batch './modules/batch.bicep' = {
  name: 'batch'
  scope: resourceGroup
  params: {
    location: location
    accountName: batchAccountName
    deployPool: deployBatchPool
    autoscalePoolName: batchPoolName
    alwaysOnPoolName: alwaysOnBatchPoolName
    tags: tags
  }
}

module containerEnvironment './modules/container-environment.bicep' = {
  name: 'container-environment'
  scope: resourceGroup
  params: {
    location: location
    name: containerEnvironmentName
    tags: tags
    logAnalyticsName: logAnalyticsName
  }
  dependsOn: [
    logAnalytics
  ]
}

module containerApp './modules/container-app.bicep' = {
  name: 'container-app'
  scope: resourceGroup
  params: {
    location: location
    name: containerAppName
    tags: tags
    environmentName: containerEnvironmentName
    registryName: containerRegistryName
    containerImage: containerImage
    applicationInsightsConnectionString: applicationInsights.outputs.connectionString
    batchAccountEndpoint: batch.outputs.accountEndpoint
    batchPoolName: batchPoolName
    alwaysOnBatchPoolName: alwaysOnBatchPoolName
  }
  dependsOn: [
    containerEnvironment
    containerRegistry
  ]
}

module roleAssignments './modules/role-assignments.bicep' = {
  name: 'role-assignments'
  scope: resourceGroup
  params: {
    acrName: containerRegistryName
    batchAccountName: batchAccountName
    keyVaultName: keyVaultName
    containerAppPrincipalId: containerApp.outputs.principalId
    deployerObjectId: deployerObjectId
  }
  dependsOn: [
    keyVault
  ]
}

output resourceGroupName string = resourceGroup.name
output containerAppName string = containerAppName
output containerAppFqdn string = containerApp.outputs.fqdn
output containerRegistryName string = containerRegistryName
output batchAccountName string = batchAccountName
output batchPoolName string = batchPoolName
output keyVaultName string = keyVaultName
