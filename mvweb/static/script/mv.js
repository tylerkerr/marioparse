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
  if (dayButton) {
    dayButton.addEventListener('click', () => {
      startDate.value = moment().subtract(1, 'days').format("YYYY-MM-DD");
    });
  }
});

window.addEventListener('DOMContentLoaded', function () {
  let weekButton = document.getElementById('weekButton');
  let startDate = document.getElementById('startDate');
  if (weekButton) {
    weekButton.addEventListener('click', () => {
      startDate.value = moment().subtract(7, 'days').format("YYYY-MM-DD");
    });
  }
});

window.addEventListener('DOMContentLoaded', function () {
  let monthButton = document.getElementById('monthButton');
  let startDate = document.getElementById('startDate');
  if (monthButton) {
    monthButton.addEventListener('click', () => {
      startDate.value = moment().subtract(1, 'months').format("YYYY-MM-DD");
    });
  }
});