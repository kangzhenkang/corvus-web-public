(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvFocus', cvFocus);

  /* @ngInject */
  function cvFocus($timeout) {
    var directive = {
      link: link,
      restrict: 'A',
    };
    return directive;

    function link(scope, element, attrs) {
      $timeout(function() {
        element[0].focus();
      });
    }
  }
})();
