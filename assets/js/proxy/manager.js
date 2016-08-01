(function() {
  'use strict';

  angular
    .module('corvus')
    .controller('ProxyManagerController', ProxyManagerController);

  /* @ngInject */
  function ProxyManagerController($scope, $rootScope, $state, $stateParams,
                                  $mdDialog, proxyService, cmdService, notify) {
    var manager = this;

    manager.updateProxy = proxyService.openUpdate;
    manager.executeCommand = cmdService.popup;
    manager.version = manager.cluster = null;
    manager.updateAll = updateAll;
    manager.registerAll = registerAll;
    manager.count = 0;

    manager.registerProxy = proxyService.register;
    manager.deregisterProxy = proxyService.deregister;

    manager.page = 1;

    manager.cluster = $stateParams.cluster || null;
    manager.version = $stateParams.version || null;
    manager.registered = $stateParams.registered || null;

    var searchSpec = [];
    if (manager.cluster) {
      searchSpec.push('c:' + manager.cluster);
    }
    if (manager.version) {
      searchSpec.push('v:' + manager.version);
    }
    if (manager.registered) {
      searchSpec.push('r:' + manager.registered);
    }
    $rootScope.globalNav.search = searchSpec.join(', ');

    $scope.$on('scrolled', onScroll);
    $scope.$watch('globalNav.search', search);
    activate(1);

    function activate(page) {
      proxyService.getProxyList(manager, page, function(data) {
        manager.count = data.count;
        manager.page = data.page;
        manager.pages = data.pages;
        var newItems = data.items;
        angular.forEach(newItems, function(v) {
          v.statusClass = v.alive ? 'label-green' : 'label-red';
        });
        manager.items = (manager.items || []).concat(newItems);
      });
    }

    function updateAll() {
      $mdDialog.show({
        templateUrl: '/static/template/update.html',
        controller: 'ProxyUpdateAllController',
        controllerAs: 'updater',
        bindToController: true,
        locals: {
          version: manager.version,
          cluster: manager.cluster,
          registered: manager.registered,
        }
      });
    }

    function registerAll() {
      manager.registering = true;
      proxyService.registerAll({
        version: manager.version,
        cluster: manager.cluster,
        registered: manager.registered
      }).then(function(response) {
        manager.registering = false;
        if (response.data.status === -1) {
          notify.warn(response.data.message);
        } else {
          notify.notice('成功注册');
        }
      }, function(err) {
        manager.registering = false;
        notify.warn(err.data.message);
      });
    }

    function onScroll() {
      if (manager.page + 1 > manager.pages) {
        return;
      }
      manager.page++;
      activate(manager.page);
    }

    // version:0.2.0, cluster: hello-world
    function search(value, old) {
      if (value == old) { return; }

      value = value.trim();
      var version = null, cluster = null, registered = null;
      var parts = value.split(',');
      angular.forEach(parts, function(v) {
        v = v.trim();
        if (!v) {
          return;
        }
        if (v.startsWith('v:') || v.startsWith('version:')) {
          version = v.split(':')[1].trim();
        } else if (v.startsWith('c:') || v.startsWith('cluster:')) {
          cluster = v.split(':')[1].trim();
        } else if (v.startsWith('r:') || v.startsWith('registered:')) {
          registered = v.split(':')[1].trim();
        } else {
          cluster = v.trim();
        }
      });
      manager.version = version;
      manager.cluster = cluster;
      manager.registered = registered;
      manager.items = [];
      activate(1);
      var params = {action: 'proxy'};
      if (version) {
        params.version = version;
      }
      if (cluster) {
        params.cluster = cluster;
      }
      if (registered) {
        params.registered = registered;
      }

      $state.transitionTo('i', params, {notify: false});
    }
  }
})();
