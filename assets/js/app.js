(function() {
  'use strict';

  angular
    .module('corvus', [
      'ui.router',
      'md.data.table',
      'ngMaterial',
      'ngMdIcons',
      'ngMessages',
    ])
    .run(run);

  /* @ngInject */
  function run($rootScope, $state) {
    $rootScope.$state = $state;
    $rootScope.globalNav = {
      nodeInfo: false,
      taskInfo: false,
      search: '',
      disableSearch: false,
      disable: true,
      title: '',
      scroll: scroll,
      clusterDisplayStats: true,
    };

    $rootScope.$on('$stateChangeSuccess', function() {
      $rootScope.globalNav.search = '';
    });

    function scroll(reachBottom) {
      if (reachBottom) {
        $rootScope.$broadcast('scrolled');
      }
      $rootScope.$broadcast('checkIfShouldStick');
    }
  }
})();
