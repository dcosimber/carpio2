(() => {
  "use strict";

  const buildButton = (label, onClick, options = {}) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.disabled = Boolean(options.disabled);
    button.setAttribute("aria-label", options.ariaLabel || label);
    if (options.current) {
      button.setAttribute("aria-current", "page");
    }
    button.addEventListener("click", onClick);
    return button;
  };

  const visiblePages = (currentPage, pageCount) => {
    const candidates = new Set([1, pageCount]);
    for (let page = currentPage - 2; page <= currentPage + 2; page += 1) {
      if (page >= 1 && page <= pageCount) candidates.add(page);
    }
    return [...candidates].sort((left, right) => left - right);
  };

  const enhanceTable = (wrapper) => {
    const table = wrapper.querySelector("table");
    const body = table?.tBodies[0];
    const rows = body ? Array.from(body.rows) : [];
    const pageSize = Number.parseInt(wrapper.dataset.pageSize || "10", 10);
    if (!table || rows.length === 0 || !Number.isInteger(pageSize) || pageSize < 1) {
      return;
    }

    const pageCount = Math.ceil(rows.length / pageSize);
    let currentPage = 1;
    const navigation = document.createElement("nav");
    navigation.className = "sample-pagination";
    navigation.setAttribute("aria-label", "Paginación de la tabla de muestras");
    navigation.setAttribute("aria-controls", table.id);
    const status = document.createElement("p");
    status.className = "sample-pagination-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    const render = (requestedPage) => {
      currentPage = Math.min(Math.max(requestedPage, 1), pageCount);
      const firstRow = (currentPage - 1) * pageSize;
      const lastRow = Math.min(firstRow + pageSize, rows.length);
      rows.forEach((row, index) => {
        row.hidden = index < firstRow || index >= lastRow;
      });

      status.textContent = `Mostrando bibliotecas ${firstRow + 1}–${lastRow} de ${rows.length}; página ${currentPage} de ${pageCount}.`;
      navigation.replaceChildren(status);
      navigation.append(
        buildButton("Primera", () => render(1), {
          disabled: currentPage === 1,
          ariaLabel: "Ir a la primera página",
        }),
        buildButton("Anterior", () => render(currentPage - 1), {
          disabled: currentPage === 1,
          ariaLabel: "Ir a la página anterior",
        }),
      );

      let previousPage = 0;
      visiblePages(currentPage, pageCount).forEach((page) => {
        if (page - previousPage > 1) {
          const ellipsis = document.createElement("span");
          ellipsis.className = "sample-pagination-ellipsis";
          ellipsis.textContent = "…";
          ellipsis.setAttribute("aria-hidden", "true");
          navigation.append(ellipsis);
        }
        navigation.append(
          buildButton(String(page), () => render(page), {
            current: page === currentPage,
            ariaLabel: `Ir a la página ${page}`,
          }),
        );
        previousPage = page;
      });

      navigation.append(
        buildButton("Siguiente", () => render(currentPage + 1), {
          disabled: currentPage === pageCount,
          ariaLabel: "Ir a la página siguiente",
        }),
        buildButton("Última", () => render(pageCount), {
          disabled: currentPage === pageCount,
          ariaLabel: "Ir a la última página",
        }),
      );
    };

    wrapper.insertAdjacentElement("afterend", navigation);
    render(1);
  };

  const initialise = () => {
    document.querySelectorAll("[data-sample-table-pagination]").forEach(enhanceTable);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
