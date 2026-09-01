(() => {
  "use strict";

  const TABLE_SELECTOR = "[data-table-pagination], [data-sample-table-pagination]";

  const buildButton = (label, onClick, options = {}) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.disabled = Boolean(options.disabled);
    button.setAttribute("aria-label", options.ariaLabel || label);
    if (options.disabled) {
      button.setAttribute("aria-disabled", "true");
    }
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

  const ensureTableId = (table, index) => {
    if (!table.id) {
      table.id = `paginated-table-${index + 1}`;
    }
    return table.id;
  };

  const describeTable = (wrapper) => (
    wrapper.dataset.tableLabel
      || wrapper.getAttribute("aria-label")
      || "tabla"
  );

  const enhanceTable = (wrapper, index) => {
    if (wrapper.dataset.paginationEnhanced === "true") {
      return;
    }
    const table = wrapper.querySelector("table");
    const body = table?.tBodies[0];
    const rows = body ? Array.from(body.rows) : [];
    const pageSize = Number.parseInt(wrapper.dataset.pageSize || "10", 10);
    if (!table || rows.length === 0 || !Number.isInteger(pageSize) || pageSize < 1) {
      return;
    }

    wrapper.dataset.paginationEnhanced = "true";
    const tableId = ensureTableId(table, index);
    const tableLabel = describeTable(wrapper);
    const pageCount = Math.ceil(rows.length / pageSize);
    let currentPage = 1;
    const navigation = document.createElement("nav");
    navigation.className = "sample-pagination";
    navigation.id = `${tableId}-pagination`;
    navigation.setAttribute("aria-label", `Paginación de ${tableLabel}`);
    navigation.setAttribute("aria-controls", tableId);
    const status = document.createElement("p");
    status.className = "sample-pagination-status";
    status.id = `${tableId}-pagination-status`;
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    const describedBy = table.getAttribute("aria-describedby");
    table.setAttribute(
      "aria-describedby",
      [describedBy, status.id].filter(Boolean).join(" "),
    );

    const render = (requestedPage) => {
      currentPage = Math.min(Math.max(requestedPage, 1), pageCount);
      const firstRow = (currentPage - 1) * pageSize;
      const lastRow = Math.min(firstRow + pageSize, rows.length);
      rows.forEach((row, rowIndex) => {
        row.hidden = rowIndex < firstRow || rowIndex >= lastRow;
      });

      status.textContent = `Mostrando filas ${firstRow + 1}–${lastRow} de ${rows.length} en la ${tableLabel}; página ${currentPage} de ${pageCount}.`;
      navigation.replaceChildren(status);
      navigation.append(
        buildButton("Primera", () => render(1), {
          disabled: currentPage === 1,
          ariaLabel: `Ir a la primera página de la ${tableLabel}`,
        }),
        buildButton("Anterior", () => render(currentPage - 1), {
          disabled: currentPage === 1,
          ariaLabel: `Ir a la página anterior de la ${tableLabel}`,
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
            ariaLabel: `Ir a la página ${page} de la ${tableLabel}`,
          }),
        );
        previousPage = page;
      });

      navigation.append(
        buildButton("Siguiente", () => render(currentPage + 1), {
          disabled: currentPage === pageCount,
          ariaLabel: `Ir a la página siguiente de la ${tableLabel}`,
        }),
        buildButton("Última", () => render(pageCount), {
          disabled: currentPage === pageCount,
          ariaLabel: `Ir a la última página de la ${tableLabel}`,
        }),
      );
    };

    wrapper.insertAdjacentElement("afterend", navigation);
    render(1);
  };

  const initialise = () => {
    document.querySelectorAll(TABLE_SELECTOR).forEach(enhanceTable);
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
})();
