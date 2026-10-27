# Version indépendante en R de base : aucune dépendance CRAN.
# Exécuter depuis la racine : Rscript scripts/analyse.R
# Données fournies pour la SAÉ ; résultats R enregistrés dans reports/r/.
raw <- read.csv('data/raw/monthly_demand.csv', stringsAsFactors = FALSE)
raw$date <- as.Date(raw$date)
raw$demand[raw$demand < 0] <- NA_real_
# split conserve les groupes dont la valeur est manquante.
groups <- split(raw$demand, as.character(raw$date))
dates <- seq(min(raw$date), max(raw$date), by='month')
y <- vapply(as.character(dates), function(d) {
  v <- groups[[d]]
  if (is.null(v) || all(is.na(v))) NA_real_ else median(v, na.rm=TRUE)
}, numeric(1))
imputed <- is.na(y)
for (i in seq_along(y)) {
  if (is.na(y[i])) {
    if (i == 1) stop('Première valeur manquante')
    y[i] <- if (i > 12) y[i-12] else median(y[seq_len(i-1)])
  }
}
stopifnot(length(y)==96, all(is.finite(y)), !any(imputed[85:96]))
features <- function(t) data.frame(t=t,s1=sin(2*pi*t/12),c1=cos(2*pi*t/12),
                                  s2=sin(4*pi*t/12),c2=cos(4*pi*t/12))
predict_model <- function(train,h,model) {
  if (model=='Saisonnier naif') return(rep(tail(train,12),length.out=h))
  if (model=='Regression harmonique') {
    df <- features(seq_along(train)-1); df$y <- as.numeric(train)
    fit <- lm(y~.,data=df)
    return(as.numeric(predict(fit,features(length(train)+(0:(h-1))))))
  }
  fit <- HoltWinters(ts(train,frequency=12),seasonal='additive')
  as.numeric(predict(fit,n.ahead=h))
}
models <- c('Saisonnier naif','Regression harmonique','Holt-Winters')
rows <- list()
for (origin in c(48,60,72)) {
  train <- y[1:origin]; ids <- (origin+1):(origin+12); valid <- !imputed[ids]
  for (model in models) {
    pred <- predict_model(train,12,model)
    e <- y[ids][valid]-pred[valid]
    rows[[length(rows)+1]] <- data.frame(model=model,origin=origin,MAE=mean(abs(e)),RMSE=sqrt(mean(e^2)))
  }
}
cv <- do.call(rbind,rows)
rank <- aggregate(cbind(MAE,RMSE)~model,cv,mean)
rank <- rank[order(rank$MAE),]
best <- rank$model[1]
pred <- predict_model(y[1:84],12,best)
future <- predict_model(y,12,best)
dir.create('reports/r',recursive=TRUE,showWarnings=FALSE)
write.csv(cv,'reports/r/cross_validation.csv',row.names=FALSE)
write.csv(rank,'reports/r/model_comparison.csv',row.names=FALSE)
write.csv(data.frame(date=dates[85:96],actual=y[85:96],prediction=pred),
          'reports/r/test_predictions.csv',row.names=FALSE)
write.csv(data.frame(date=seq(as.Date('2026-01-01'),by='month',length.out=12),prediction=future),
          'reports/r/future_forecast.csv',row.names=FALSE)
df <- features(0:83);df$y <- as.numeric(y[1:84])
fit <- lm(y~.,data=df)
# Tests R classiques : hypothèses iid plus fortes que la covariance HAC en Python.
sink('reports/r/statistical_tests.txt')
cat('ANALYSE STATISTIQUE SAE - inférence exploratoire, erreurs iid supposées\n')
print(summary(fit))
print(anova(lm(y~t,data=df),fit))
print(shapiro.test(residuals(fit)))
print(Box.test(residuals(fit),lag=12,type='Ljung-Box'))
cat('\nModèle :',best,'\nMAE test :',mean(abs(y[85:96]-pred)),'\n')
print(sessionInfo())
sink()
png('reports/r/decomposition.png',width=1200,height=900)
plot(stl(ts(y[1:84],start=c(2018,1),frequency=12),s.window='periodic',robust=TRUE))
dev.off()
cat('Résultats R dans reports/r/\n')
