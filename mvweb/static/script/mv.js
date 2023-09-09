window.addEventListener('DOMContentLoaded', function () {
  let forms = document.getElementsByClassName('skipEmptyFields');
  for (let form of forms) {
    form.addEventListener('formdata', function (event) {
      let formData = event.formData;
      for (let [name, value] of Array.from(formData.entries())) {
        if (value === '') formData.delete(name);
      }
    });
  }
});

(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const corpChecks = document.querySelectorAll('.corpstat');
    corpChecks.forEach(corpCheck => {
      corpCheck.addEventListener('mouseover', event => {
        if (corpCheck !== event.target) return;
        let tipDiv = event.target.querySelector('.corptooltip');
        tipDiv.dataset.moused = '1';
        if (tipDiv.innerHTML.trim() == '') {
          let corp = event.target.querySelector('.corplink').innerHTML.trim();
          let sessionCheck = sessionStorage.getItem('corp-' + corp)
          if (sessionCheck === null) {
            let xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function () {
              if (xhr.readyState == XMLHttpRequest.DONE) {
                xresp = xhr.responseText;
                sessionStorage.setItem('corp-' + corp, xresp)
                tipDiv.innerHTML = sessionStorage.getItem('corp-' + corp)
                if (tipDiv.dataset.moused === '1') {
                  tipDiv.style.display = 'block';
                }
              }
            }
            url = '/api/snuggly/corp/' + corp;
            xhr.responseType = 'text';
            xhr.open('GET', url);
            xhr.send();
          } else {
            tipDiv.innerHTML = sessionStorage.getItem('corp-' + corp)
            tipDiv.style.display = 'block';
          }
        } else {
          tipDiv.style.display = 'block';
        }
      })
    });
    corpChecks.forEach(corpCheck => {
      corpCheck.addEventListener('mouseleave', event => {
        let tipDiv = event.target.querySelector('.corptooltip');
        tipDiv.dataset.moused = '0';
        tipDiv.style.display = 'none';
      });
    })
  });
})();


(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const pilotChecks = document.querySelectorAll('.pilotstat');
    pilotChecks.forEach(pilotCheck => {
      pilotCheck.addEventListener('mouseover', event => {
        if (pilotCheck !== event.target) return;
        let tipDiv = event.target.querySelector('.pilottooltip');
        tipDiv.dataset.moused = '1';
        if (tipDiv.innerHTML.trim() == '') {
          let pilot = event.target.querySelector('.pilotlink').innerHTML.trim();
          let sessionCheck = sessionStorage.getItem('pilot-' + pilot)
          if (sessionCheck === null) {
            let xhr = new XMLHttpRequest();
            xhr.onreadystatechange = function () {
              if (xhr.readyState == XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                  xresp = xhr.responseText;
                } else {
                  xresp = 'n/a'
                }
                sessionStorage.setItem('pilot-' + pilot, xresp)
                tipDiv.innerHTML = sessionStorage.getItem('pilot-' + pilot)
                if (tipDiv.dataset.moused === '1') {
                  tipDiv.style.display = 'block';
                }
              }
            }
            if (pilot.indexOf('/') > -1) {
              pilot = encodeURIComponent(encodeURIComponent(pilot));
            }
            url = '/api/snuggly/pilot/' + pilot;
            xhr.responseType = 'text';
            xhr.open('GET', url);
            xhr.send();
          } else {
            tipDiv.innerHTML = sessionStorage.getItem('pilot-' + pilot)
            tipDiv.style.display = 'block';
          }
        } else {
          tipDiv.style.display = 'block';
        }
      })

    });
    pilotChecks.forEach(pilotCheck => {
      pilotCheck.addEventListener('mouseleave', event => {
        let tipDiv = event.target.querySelector('.pilottooltip');
        tipDiv.dataset.moused = '0';
        tipDiv.style.display = 'none';
      });
    })
  });
})();

/* hp-toggle */
/* relevant classes:
  .hp-toggle: master class
  .hp-highlight: give it cursor and link-style mouseover color
  .hp-control: this is a control button so never hide it
  .hp-display: this is the actual info display so don't give it an onclick to hide itself */
(() => {
  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll('.hp-toggle').forEach(el => {
      const { group } = el.dataset;
      const toggleClass = el.dataset.class || 'hidden';
      if (el.classList.contains('hp-display')) return;
      el.addEventListener('click', () => {
        document.querySelectorAll(`.hp-toggle[data-group="${group}"]`).forEach(e => {
          if (e.classList.contains('hp-control')) return;
          e.classList.toggle(toggleClass);
        });
      });
    });
  });
})();

(() => {
  document.addEventListener("DOMContentLoaded", () => {
    const dateCells = document.querySelectorAll('.moment');
    dateCells.forEach(cell => {
      date = cell.innerHTML
      mom = moment.utc(date);
      cell.innerHTML = mom.fromNow();
      cell.title = date;
    })
  });
})();

window.addEventListener('DOMContentLoaded', function () {
  let dayButton = document.getElementById('dayButton');
  let startDate = document.getElementById('startDate');
  dayButton.addEventListener('click', () => {
    startDate.value = moment().subtract(1, 'days').format("YYYY-MM-DD");
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let dayButton = document.getElementById('weekButton');
  let startDate = document.getElementById('startDate');
  dayButton.addEventListener('click', () => {
    startDate.value = moment().subtract(7, 'days').format("YYYY-MM-DD");
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let dayButton = document.getElementById('monthButton');
  let startDate = document.getElementById('startDate');
  dayButton.addEventListener('click', () => {
    startDate.value = moment().subtract(1, 'months').format("YYYY-MM-DD");
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let swapButton = document.getElementById('corpswap');
  let killer_corp = document.querySelector('input[name=killer_corp]')
  let kc_val = killer_corp.value
  let victim_corp = document.querySelector('input[name=victim_corp]')
  let vc_val = victim_corp.value
  let searchForm = document.getElementById('mainsearchform');
  if (kc_val !== '' || vc_val !== '') {
    swapButton.removeAttribute("disabled");
  }
  swapButton.addEventListener('click', () => {
    killer_corp.setAttribute("value", vc_val)
    victim_corp.setAttribute("value", kc_val)
    searchForm.submit()
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let swapButton = document.getElementById('nameswap');
  let killer_name = document.querySelector('input[name=killer_name]')
  let kn_val = killer_name.value
  let victim_name = document.querySelector('input[name=victim_name]')
  let vn_val = victim_name.value
  let searchForm = document.getElementById('mainsearchform');
  if (kn_val !== '' || vn_val !== '') {
    swapButton.removeAttribute("disabled");
  }
  swapButton.addEventListener('click', () => {
    killer_name.setAttribute("value", vn_val)
    victim_name.setAttribute("value", kn_val)
    searchForm.submit()
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let swapButton = document.getElementById('shipswap');
  let killer_ship= document.querySelector('input[name=killer_ship_type]')
  let ks_val = killer_ship.value
  let victim_ship = document.querySelector('input[name=victim_ship_type]')
  let vs_val = victim_ship.value
  let searchForm = document.getElementById('mainsearchform');
  if (ks_val !== '' || vs_val !== '') {
    swapButton.removeAttribute("disabled");
  }
  swapButton.addEventListener('click', () => {
    killer_ship.setAttribute("value", vs_val)
    victim_ship.setAttribute("value", ks_val)
    searchForm.submit()
  });
});

window.addEventListener('DOMContentLoaded', function () {
  let swapButton = document.getElementById('classswap');
  let killer_ship_category = document.querySelector('input[name=killer_ship_category]')
  let ksc_val = killer_ship_category.value
  let victim_ship_category = document.querySelector('input[name=victim_ship_category]')
  let vsc_val = victim_ship_category.value
  let searchForm = document.getElementById('mainsearchform');
  if (ksc_val !== '' || vsc_val !== '') {
    swapButton.removeAttribute("disabled");
  }
  swapButton.addEventListener('click', () => {
    killer_ship_category.setAttribute("value", vsc_val)
    victim_ship_category.setAttribute("value", ksc_val)
    searchForm.submit()
  });
});