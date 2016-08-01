(function() {
  'use strict';

  angular
    .module('corvus')
    .directive('cvStick', cvStick);

  /* @ngInject */
  function cvStick() {
    var directive = {
      link: link,
      restrict: 'A'
    };
    return directive;

    var placeholder = null;

    function link(scope, nav, attrs) {
      var upLine = null;
      var initStyle = null;
      var navFixed = false;
      var addedPlaceholder = false;

      scope.$on('checkIfShouldStick', function() {
        var viewport = findViewport(nav);
        if (upLine === null) {
          upLine = getUpLine(nav[0], viewport);
          initStyle = getStyle(nav[0]);
        }
        if (!navFixed && viewport.scrollTop > upLine) {
          // add holder here for chrome
          if (!addedPlaceholder) {
            addPlaceholder(nav);
            addedPlaceholder = true;
          }
          var lastStyle = getStyle(nav[0]);
          var paddingTop = parseInt(initStyle.paddingTop.replace(/px/, ''))
                         + parseInt(attrs.stickTop.replace(/px/, ''));
          nav.css('position', 'fixed')
             .css('z-index', '10')
             .css('top', '0')
             .css('padding-top', paddingTop + 'px')
             .css('padding-left', initStyle.paddingLeft)
             .css('width', lastStyle.width);
          navFixed = true;
        } else if (navFixed && viewport.scrollTop <= upLine) {
          nav.css('position', 'relative')
             .css('width', 'auto')
             .css('padding-top', initStyle.paddingTop)
             .css('padding-left', initStyle.paddingLeft)
             .css('top', initStyle.top);
          navFixed = false;
        }
      });
    }

    function findViewport(element) {
      var p = element;
      do {
        var n = p[0];
        if (n.isScrollingViewport) {
          return n;
        }
        p = p.parent();
      } while(p.length !== 0);
      return null;
    }

    function getStyle(elem) {
      var computedStyle = window.getComputedStyle(elem) || elem.currentStyle;
      var result = {
        width: computedStyle.width,
        padding: computedStyle.padding,
        paddingTop: computedStyle.padding,
        paddingLeft: computedStyle.padding,
        top: computedStyle.top,
        marginTop: computedStyle.marginTop,
        marginBottom: computedStyle.marginBottom,
        borderTopWidth: computedStyle.borderTopWidth,
        borderBottomWidth: computedStyle.borderBottomWidth,
      };
      if (result.padding === "") {
        // firefox
        result.paddingTop = computedStyle["padding-top"];
        result.paddingLeft = computedStyle["padding-left"];
      }
      return result;
    }

    function getUpLine(elem, viewport) {
      var box = elem.getBoundingClientRect();
      if (box.height) {
        return box.height;  // some browser support `height`
      }
      var clientTop = document.documentElement.clientTop || document.body.clientTop || 0;
      var top  = box.top - clientTop;
      // The `top` below is accurate, but will result in trembling
      // var top  = box.top + viewport.scrollTop - clientTop;
      return Math.round(top);
    }

    function createPlaceholder(nav) {
      if (placeholder) {
        return placeholder;
      }
      placeholder = angular.element('<div></div>');
      var elementsHeight = nav[0].offsetHeight;
      var computedStyle = getStyle(nav[0])
      elementsHeight += parseInt(computedStyle.marginTop);
      elementsHeight += parseInt(computedStyle.marginBottom);
      elementsHeight += parseInt(computedStyle.borderTopWidth);
      elementsHeight += parseInt(computedStyle.borderBottomWidth);
      placeholder.css('height', elementsHeight + 'px')
                 .css('margin', '0px')
                 .css('padding', '0px');
      return placeholder;
    }

    function addPlaceholder(nav) {
      var navbar = nav[0];
      var parent = nav.parent()[0];
      var holder = createPlaceholder(nav)[0];
      parent.removeChild(navbar);
      holder.appendChild(navbar);
      parent.insertBefore(holder, parent.firstChild);
    }
  }
})();
