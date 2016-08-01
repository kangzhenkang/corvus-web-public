(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvNodesToggle', cvNodesToggle);

  /* @ngInject */
  function cvNodesToggle($state, $location, $timeout, $anchorScroll) {
    var directive = {
      link: link,
      restrict: 'A',
      scope: {
        cvNodesToggle: '@',
        ngClick: '&',
      }
    };
    return directive;

    function link(scope, element) {
      if ($state.is('cluster') && $location.hash() == scope.cvNodesToggle) {
        scope.ngClick();
        $timeout(function() {
          $anchorScroll();
        }, 300);
      }
    }
  }
})();
