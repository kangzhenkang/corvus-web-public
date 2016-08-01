(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('AgentManagerController', AgentManagerController);

  /* @ngInject */
  function AgentManagerController($scope, $rootScope, $state, $stateParams,
                                  $mdDialog, agentService, notify) {
    var manager = this;

    manager.updateAgent = updateAgent;
    manager.updateAll = updateAll;
    manager.count = 0;
    manager.page = 1;

    manager.host = $stateParams.host || null;

    var searchSpec = '';
    if ($stateParams.host) {
      manager.host = $stateParams.host;
      searchSpec = manager.host;
    }
    $rootScope.globalNav.search = searchSpec;

    $scope.$on('scrolled', onScroll);
    $scope.$watch('globalNav.search', search);
    activate(1);

    function activate(page) {
      agentService.getAgentList(manager, page, function(data) {
        manager.count = data.count;
        manager.pages = data.pages;
        manager.page = data.page;
        var newItems = data.items;
        angular.forEach(newItems, function(v) {
          v.statusClass = v.alive ? 'label-green' : 'label-red';
        });
        manager.items = (manager.items || []).concat(newItems);
      });
    }

    function updateAgent(item) {
      $mdDialog.show({
        templateUrl: '/static/template/update.html',
        controller: 'AgentUpdateController',
        controllerAs: 'updater',
        bindToController: true,
        locals: {
          host: item.host,
          port: item.port,
        }
      });
    }

    function updateAll() {
      $mdDialog.show({
        templateUrl: '/static/template/update.html',
        controller: 'AgentUpdateAllController',
        controllerAs: 'updater',
        bindToController: true,
        locals: {
          host: manager.host
        }
      });
    }

    function onScroll() {
      manager.page++;
      if (manager.page > manager.pages) {
        return;
      }
      activate(manager.page);
    }

    function search(value, old) {
      if (value == old) { return; }

      manager.host = value.trim();
      manager.items = [];
      activate(1);
      var params = {action: 'agent'};
      if (manager.host) {
        params.host = manager.host;
      }
      $state.transitionTo('i', params, {notify: false});
    }
  }
})();
