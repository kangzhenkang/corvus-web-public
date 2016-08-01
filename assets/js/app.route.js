(function() {
  'use strict';

  var navs = {
    node: {
      model: 'NodeInfoController as nodeInfo',
      template: '/static/template/node/info.html',
      title: '节点信息',
    },
    task: {
      model: 'TaskInfoController as taskInfo',
      template: '/static/template/taskInfo.html',
      title: '任务信息',
    },
    proxy: {
      model: 'ProxyManagerController as manager',
      template: '/static/template/proxy/manager.html',
      title: '代理管理',
      search: true,
    },
    agent: {
      model: 'AgentManagerController as manager',
      template: '/static/template/agent/manager.html',
      title: 'agent 管理',
      search: true,
    }
  };

  angular
    .module('corvus')
    .config(config);

  /* @ngInject */
  function config($locationProvider, $stateProvider, $urlRouterProvider, $uiViewScrollProvider) {
    $uiViewScrollProvider.useAnchorScroll();
    $urlRouterProvider.otherwise('/');

    $stateProvider
      .state('cluster', {
        url: '/?q',
        views: {
          'navbar': {
            templateUrl: '/static/template/cluster/switch.html',
            controller: function($rootScope) { this.globalNav = $rootScope.globalNav },
            controllerAs: 'nav',
          },
          '': {
            templateUrl: '/static/template/cluster/cluster.html',
            controller: 'ClusterController',
            controllerAs: 'cluster',
          }
        }
      })
      .state('node', {
        url: '/node?q',
        templateUrl: '/static/template/node/node.html',
        controller: 'NodeController',
        controllerAs: 'node',
      })
      .state('i', {
        url: '/i/{action}?nodeId&taskId&cluster&version&registered',
        templateUrl: navTemplate,
        controllerProvider: navControllerProvider,
        onEnter: navOnEnter,
        onExit: navOnExit,
      })
      .state('task', {
        url: '/task?q',
        templateUrl: '/static/template/task.html',
        controller: 'TaskController',
        controllerAs: 'task',
      });

    /* @ngInject */
    function navControllerProvider($stateParams) {
      return navs[$stateParams.action].model;
    }

    function navTemplate(stateParams) {
      return navs[stateParams.action].template;
    }

    /* @ngInject */
    function navOnEnter($rootScope, $stateParams) {
      $rootScope.globalNav.disableSearch = !navs[$stateParams.action].search;
      $rootScope.globalNav.disable = false;
      $rootScope.globalNav.title = navs[$stateParams.action].title;
    }

    /* @ngInject */
    function navOnExit($rootScope) {
      $rootScope.globalNav.disable = true;
      $rootScope.globalNav.title = '';
      $rootScope.globalNav.disableSearch = false;
    }

    $locationProvider.html5Mode(true);
  }
})();
