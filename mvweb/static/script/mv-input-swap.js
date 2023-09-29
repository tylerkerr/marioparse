
const corpswap = function () {
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
  }
  
const nameswap = function () {
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
  }
  
const shipswap = function () {
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
  }
  
const classwap = function () {
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
  }

corpswap();
nameswap();
shipswap();
classswap();