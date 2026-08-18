param name string
param location string
param tags object

resource storageAccount 'Microsoft.Storage/storageAccounts@2026-04-01' = {
  name: name
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource resultsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2024-01-01' = {
  name: '${storageAccount.name}/default/results'
  properties: {
    publicAccess: 'None'
  }
}

output id string = storageAccount.id
