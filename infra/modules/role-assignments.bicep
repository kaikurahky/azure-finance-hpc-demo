param acrName string
param batchAccountName string
param keyVaultName string
param containerAppPrincipalId string
param deployerObjectId string = ''

var acrPullRoleId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
var batchDataContributorRoleId = '6aaa78f1-f7de-44ca-8722-c64a23943cae'
var keyVaultSecretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'

resource registry 'Microsoft.ContainerRegistry/registries@2025-11-01' existing = {
  name: acrName
}

resource batchAccount 'Microsoft.Batch/batchAccounts@2025-06-01' existing = {
  name: batchAccountName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, containerAppPrincipalId, acrPullRoleId)
  scope: registry
  properties: {
    principalId: containerAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleId)
  }
}

resource batchDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(batchAccount.id, containerAppPrincipalId, batchDataContributorRoleId)
  scope: batchAccount
  properties: {
    principalId: containerAppPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', batchDataContributorRoleId)
  }
}

resource deployerKeyVaultOfficer 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(deployerObjectId)) {
  name: guid(keyVault.id, deployerObjectId, keyVaultSecretsOfficerRoleId)
  scope: keyVault
  properties: {
    principalId: deployerObjectId
    principalType: 'User'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsOfficerRoleId)
  }
}
